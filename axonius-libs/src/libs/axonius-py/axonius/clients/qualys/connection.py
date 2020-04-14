import logging
from typing import List, Dict, Optional, Iterable, Generator, Union, Tuple

from axonius.clients.qualys import consts, xmltodict
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.consts import get_default_timeout
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')
'''
In this connection we target the VM module (and probably PC later on).
These modules have a rate limit - by default of 2 connections through api v2.0 or 300 api requests an hour.
For the sake of the user - if the next api request is allowed within the next 30 seconds we wait and try again.
'''


class IteratorCounter:
    def __init__(self,
                 message,
                 start_value=0,
                 threshold=50):
        self._message = message
        self._count = start_value
        self._last_printed_value = self._count
        self._threshold = threshold

    def add(self, value=1):
        self._count += value

    def print_if_needed(self):
        if self._count - self._last_printed_value >= self._threshold:
            self._last_printed_value = self._count
            self.print()
            return True
        return False

    def print(self):
        logger.info(self._message.format(count=self._count))


class QualysScansConnection(RESTConnection):

    def __init__(self,
                 *args,
                 request_timeout=None,
                 chunk_size=None,
                 devices_per_page=None,
                 retry_sleep_time=None,
                 max_retries=None,
                 date_filter=None,
                 **kwargs):
        """ Initializes a connection to Illusive using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for Illusive
        """
        request_timeout = request_timeout or consts.DEFAULT_REQUEST_TIMEOUT
        super().__init__(*args, session_timeout=(get_default_timeout().read_timeout, request_timeout), **kwargs)
        self._permanent_headers = {'X-Requested-With': 'Axonius Qualys Scans Adapter',
                                   'Accept': 'application/json'}
        self._date_filter = date_filter
        self._chunk_size = chunk_size or consts.DEFAULT_CHUNK_SIZE
        self._devices_per_page = devices_per_page or consts.DEVICES_PER_PAGE
        self._retry_sleep_time = retry_sleep_time or consts.RETRY_SLEEP_TIME
        self._max_retries = max_retries or consts.MAX_RETRIES

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No username or password')
        self._get_device_count()

    def _prepare_get_hostassets_request_params(self, start_offset):
        params = {
            'ServiceRequest': {
                'preferences': {
                    'startFromOffset': start_offset,
                    'limitResults': self._devices_per_page
                },
            }
        }
        if self._date_filter:
            # filter by 'last_seen' greater then
            params['ServiceRequest']['filters'] = {
                'Criteria': [{
                    'field': 'lastVulnScan',
                    'operator': 'GREATER',
                    'value': self._date_filter,
                }],
            }
        return {'name': 'qps/rest/2.0/search/am/hostasset/',
                'body_params': params,
                'do_basic_auth': True}

    def get_device_id_data(self, device_id):
        response = self._get(f'qps/rest/2.0/get/am/hostasset/{device_id}', do_basic_auth=True)
        if not isinstance(response, dict):
            raise RESTException(f'Bad Response not as dict: {str(response)}')
        if 'ServiceResponse' not in response:
            raise RESTException(f'Bad Response without ServiceResponse: {str(response)}')
        response = response['ServiceResponse']
        if 'data' not in response:
            raise RESTException(f'Bad response with not data: {str(response)}')
        if not isinstance(response['data'], list) or not response['data']:
            raise RESTException(f'Bad response with bad data: {str(response)}')
        return response['data'][0]

    def _get_device_count(self):
        params = {
            'ServiceRequest': {
            }
        }
        if self._date_filter:
            # filter by 'last_seen' greater then
            params['ServiceRequest']['filters'] = {
                'Criteria': [{
                    'field': 'lastVulnScan',
                    'operator': 'GREATER',
                    'value': self._date_filter,
                }],
            }
        exception_count = 0
        while True:
            try:
                result = self._post('qps/rest/2.0/count/am/hostasset', body_params=params, do_basic_auth=True)
                if not (result.get('ServiceResponse') or {}).get('count'):
                    raise RuntimeError(f'Response is {result}')
                break
            except Exception as e:
                logger.warning(f'Exception {exception_count} while fetching count error :{e}')
                exception_count += 1
                if exception_count >= consts.FETCH_EXCEPTION_THRESHOLD:
                    raise

        return result['ServiceResponse']['count']

    def _get_hostassets_by_requests(self, requests):
        for request_id, response in enumerate(self._async_post(requests, chunks=self._chunk_size,
                                                               retry_on_error=True,
                                                               max_retries=self._max_retries,
                                                               retry_sleep_time=self._retry_sleep_time)):
            try:
                if isinstance(response, Exception):
                    logger.error(f'{request_id} - Got Exception: {response}')
                    continue

                service_response = response.get('ServiceResponse') or {}
                data = service_response.get('data')
                if not data:
                    logger.error(f'{request_id} - no data. Response is {service_response}')
                    continue

                yield (request_id, data)
                self._yielded_devices_count.add(len(data))
                self._yielded_devices_count.print_if_needed()
            except Exception:
                logger.exception(f'{request_id} - Failed to deliver: {response}')

    def _get_hostassets(self):
        logger.info('Starting to fetch')
        count = self._get_device_count()
        self._yielded_devices_count = IteratorCounter(f'Got {{count}} devices so far out of {count}', threshold=100)
        logger.info(f'device count is {count}')

        offsets = range(1, count + 1, self._devices_per_page)
        requests = [self._prepare_get_hostassets_request_params(offset) for offset in offsets]

        # we try to fetch each page max exception threshold.
        # if we got data back we remove it from the next round
        # if we got all responses back we stop

        for i in range(1, consts.FETCH_EXCEPTION_THRESHOLD + 1):
            logger.info(f'Aync round number {i}, sending {len(requests)} requests')
            success_indices = []
            for index, devices in self._get_hostassets_by_requests(requests):
                yield from devices
                success_indices.append(index)

            requests = [request for i, request in enumerate(requests) if i not in success_indices]
            if not requests:
                break
        else:
            logger.error(f'Lost {len(requests) * self._devices_per_page} devices')

    def get_device_list(self):
        try:
            for device_raw in self._get_hostassets():
                yield device_raw
        except Exception:
            logger.exception(f'Problem getting hostassets')

    def add_assets_by_hostname(self, hosts: List):
        """seems like add assets by hostname isn"t implemented yet"""
        # https://github.com/paragbaxi/qualysapi/blob/master/qualysapi/api_actions.py
        raise NotImplementedError()

    def add_assets_by_ip(self, ips: List):
        """Permissions - A Manager has permissions to add IP addresses.
           A Unit Manager can add IP addresses when the “Add assets” permission is enabled in their account.
           Users with other roles (Scanner, Reader, Auditor) do not have permissions to add IP addresses."""
        try:
            ips = ','.join(ips)
            resp = self._post('api/2.0/fo/asset/ip/',
                              do_basic_auth=True,
                              use_json_in_body=False,
                              use_json_in_response=False,
                              url_params={'action': 'add'},
                              body_params={'ips': ips, 'enable_vm': 1})
            resp = xmltodict.parse(resp)
            text = resp['SIMPLE_RETURN']['RESPONSE']['TEXT']
            return text == 'IPs successfully added to Vulnerability Management', text
        except Exception as e:
            logger.debug(f'Failed with {e}')
            return False, ''

    def get_asset_by_ip(self, ips: List):
        """Permissions - A Manager has permissions to add IP addresses.
           A Unit Manager can add IP addresses when the “Add assets” permission is enabled in their account.
           Users with other roles (Scanner, Reader, Auditor) do not have permissions to add IP addresses."""
        try:
            ips = ','.join(ips)
            resp = self._post('api/2.0/fo/asset/ip/',
                              do_basic_auth=True,
                              use_json_in_body=False,
                              use_json_in_response=False,
                              url_params={'action': 'list'},
                              body_params={'ips': ips})
            resp = xmltodict.parse(resp)
            text = resp['IP_LIST_OUTPUT']['RESPONSE']['IP_SET']['IP']
            return text
        except Exception as e:
            logger.debug(f'Failed with {e}')
            return []

    def get_asset_group_id_by_title(self, title):
        try:
            resp = self._post('api/2.0/fo/asset/group/',
                              do_basic_auth=True,
                              use_json_in_body=False,
                              use_json_in_response=False,
                              url_params={'action': 'list'},
                              body_params={'title': title, 'show_attributes': 'ID'})
            resp = xmltodict.parse(resp)
            return resp['ASSET_GROUP_LIST_OUTPUT']['RESPONSE']['ID_SET']['ID']
        except Exception as e:
            logger.debug(f'Failed with {e}')
            return None

    def delete_group(self, id_):
        try:
            resp = self._post('api/2.0/fo/asset/group/',
                              do_basic_auth=True,
                              use_json_in_body=False,
                              use_json_in_response=False,
                              url_params={'action': 'delete'},
                              body_params={'id': id_})
            resp = xmltodict.parse(resp)
            text = resp['SIMPLE_RETURN']['RESPONSE']['TEXT']
            return text == 'Asset Group Deleted Successfully', text
        except Exception as e:
            logger.debug(f'Failed with {e}')
            return False, ''

    def create_group(self, title, ips: List=None, hostnames: List=None):
        try:
            if not ips:
                ips = []
            if not hostnames:
                hostnames = []

            ips = ','.join(ips)
            hostnames = ','.join(hostnames)

            body_params = {'title': title}
            if ips:
                body_params['ips'] = ips

            if hostnames:
                body_params['dns_names'] = hostnames

            resp = self._post('api/2.0/fo/asset/group/',
                              do_basic_auth=True,
                              use_json_in_body=False,
                              use_json_in_response=False,
                              url_params={'action': 'add'},
                              body_params=body_params)
            resp = xmltodict.parse(resp)

            text = resp['SIMPLE_RETURN']['RESPONSE']['TEXT']
            return text == 'Asset Group successfully added.', text
        except Exception as e:
            logger.debug(f'Failed with {e}')
            return False, ''

    def _pagination_body_generator(self, filter_criteria_list: Optional[Iterable[dict]] = None):
        # ignore initial empty response
        record_count = 0
        has_more = True
        while has_more:
            last_response = (yield self._prepare_service_request(filter_criteria_list=filter_criteria_list,
                                                                 start_offset=record_count))
            record_count += last_response.get('count', 0)
            has_more = (last_response.get('count')
                        and last_response.get('hasMoreRecords', '') == 'true')

    def _search_tags(self, fields: Optional[List[str]] = None) -> Generator[dict, None, None]:
        """Permissions required - Managers with full scope, other users must have
           Access Permission “API Access”"""
        try:
            resp = None
            query_params_str = f'?fields={",".join(fields)}' if fields else ''
            body_params_gen = self._pagination_body_generator()
            # Note: This loop ends with StopIteration exception
            while True:
                body_params = body_params_gen.send(resp)
                resp = self._post(f'qps/rest/2.0/search/am/tag{query_params_str}',
                                  do_basic_auth=True,
                                  use_json_in_body=True,
                                  use_json_in_response=False,
                                  body_params=body_params,
                                  extra_headers={'Accept': 'application/xml'})
                resp = xmltodict.parse(resp)
                service_response = self._handle_qualys_response(resp)
                tags_list = service_response['data']['Tag']
                if not isinstance(tags_list, list):
                    tags_list = [tags_list]
                yield from tags_list
        except StopIteration:
            pass
        except Exception:
            logger.exception(f'Failed search_tags')
            return

    def _search_hosts(self, filter_criteria_list: Optional[Iterable[dict]] = None,
                      fields: Optional[Iterable[str]] = None) -> Generator[dict, None, None]:
        """Permissions required - Managers with full scope, other users must have these
           permissions: Access Permission “API Access” and Asset Management
           Permission “Read Asset”"""

        try:
            logger.info(f'searching hosts by the following criterias: {filter_criteria_list}')

            resp = None
            query_params_str = f'?fields={",".join(fields)}' if fields else ''
            body_params_gen = self._pagination_body_generator(filter_criteria_list=filter_criteria_list)
            # Note: This loop ends with StopIteration exception
            while True:
                body_params = body_params_gen.send(resp)
                resp = self._post(f'qps/rest/2.0/search/am/hostasset{query_params_str}',
                                  do_basic_auth=True,
                                  use_json_in_body=True,
                                  use_json_in_response=False,
                                  body_params=body_params,
                                  extra_headers={'Accept': 'application/xml'})
                resp = xmltodict.parse(resp)
                service_response = self._handle_qualys_response(resp)

                # determine whether multiple results returned
                host_assets = service_response['data']['HostAsset']
                if isinstance(host_assets, list):
                    host_assets = [host_assets]
                yield from host_assets

        except StopIteration:
            return
        except Exception:
            logger.exception(f'Failed searching hosts - body params: {body_params}')
            return

    def list_tag_ids_by_name(self) -> Dict[str, str]:
        """ see _search_tags """
        return {tag_dict['name']: tag_dict['id'] for tag_dict in self._search_tags(fields=['id', 'name'])}

    def iter_tags_by_host_id(self, host_id_list: Optional[Iterable[str]] = None) \
            -> Generator[Tuple[str, Iterable[dict]], None, None]:
        """ see _search_hosts """

        criteria_list = []
        if host_id_list:
            criteria_list.append(self._generate_filter_criteria_for_host_ids(host_id_list))

        hosts = self._search_hosts(filter_criteria_list=criteria_list,
                                   fields=['id', 'tags.list.TagSimple.id', 'tags.list.TagSimple.name'])
        if not hosts:
            return

        for host_dict in hosts:
            tags = host_dict.get('tags', {}).get('list', {}).get('TagSimple', [])
            if not isinstance(tags, list):
                tags = [tags]
            yield host_dict['id'], tags

    def add_host_existing_tags(self, host_id_list: Iterable[str], tag_ids_to_add: Iterable[str]):
        """Permissions: see _update_hostasset"""
        logger.info(f'Adding existing tags {tag_ids_to_add} to hosts {host_id_list}')
        return self._update_hostasset_tags(host_id_list, 'add', tag_ids_to_add)

    def remove_host_tags(self, host_id_list: Iterable[str], tag_ids_to_remove: Iterable[str]):
        """Permissions: see _update_hostasset"""
        logger.info(f'Removing tags {tag_ids_to_remove} from hosts {host_id_list}')
        return self._update_hostasset_tags(host_id_list, 'remove', tag_ids_to_remove)

    def _update_hostasset_tags(self, host_id_list: Iterable[str],
                               operation_name: str, tag_id_list: Iterable[Union[str, int]]) -> dict:
        """Permissions: see _update_hostasset"""
        return self._update_hostasset(
            host_id_list,
            request_body={'data': {'HostAsset': {'tags': {operation_name: {
                'TagSimple': [{'id': tag_id} for tag_id in tag_id_list]
            }}}}})

    def _update_hostasset(self, host_id_list: Iterable[str], request_body: dict) -> dict:
        """Permissions required - Managers with full scope, other users must have the
           requested assets in their scope and these permissions: Access Permission
           “API Access” and Asset Management Permission “Update Asset”"""

        logger.info(f'Updating hosts {host_id_list} with request body: {request_body}')

        body_params = self._prepare_service_request(
            request_body=request_body,
            filter_criteria_list=[self._generate_filter_criteria_for_host_ids(host_id_list)])

        try:
            # pylint: disable=invalid-string-quote
            resp = self._post(f'qps/rest/2.0/update/am/hostasset',
                              do_basic_auth=True,
                              use_json_in_body=True,
                              use_json_in_response=False,
                              body_params=body_params,
                              extra_headers={'Accept': 'application/xml'})
            resp = xmltodict.parse(resp)
            service_response = self._handle_qualys_response(resp)
            return service_response
        except Exception:
            logger.exception(f'Failed updating hosts {host_id_list}')
            return {}

    def create_tag(self, tag_name: str, parent_tag_id: Optional[str] = None):
        """Permissions required - Managers with full scope, other users must have these
           permissions: Access Permission “API Access”, Tag Permission “Create User
           Tag”, Tag Permission “Modify Dynamic Tag Rules” (to create a dynamic tag)"""

        logger.info(f'Creating tag {tag_name} with parent {parent_tag_id}')

        # prepare request
        additional_fields_dict = {}
        if parent_tag_id:
            additional_fields_dict = {'parentTagId': parent_tag_id}

        body_params = self._prepare_service_request(
            {'data': {'Tag': {'name': tag_name, **additional_fields_dict}}})

        try:
            resp = self._post(f'qps/rest/2.0/create/am/tag',
                              do_basic_auth=True,
                              use_json_in_body=True,
                              use_json_in_response=False,
                              body_params=body_params,
                              extra_headers={'Accept': 'application/xml'})
            resp = xmltodict.parse(resp)
            service_response = self._handle_qualys_response(resp)
            created_tag_dict = service_response.get('data', {}).get('Tag', {})
            logger.debug(f'Created tag {created_tag_dict} successfully')
            return created_tag_dict
        except Exception:
            logger.exception(f'Failed creating tag {tag_name}')
            return {}

    def delete_tags(self, tag_id_list: Iterable[str]):
        """Permissions required - Managers with full scope, other users must have these
           permissions: Access Permission “API Access” and Tag Permission “Delete User Tag”"""
        logger.info(f'Deleting tags {tag_id_list}')

        body_params = self._prepare_service_request(
            filter_criteria_list=[self._generate_filter_criteria('id', 'IN', ','.join(tag_id_list))])

        try:
            resp = self._post(f'qps/rest/2.0/delete/am/tag',
                              do_basic_auth=True,
                              use_json_in_body=True,
                              use_json_in_response=False,
                              body_params=body_params,
                              extra_headers={'Accept': 'application/xml'})
            resp = xmltodict.parse(resp)
            service_response = self._handle_qualys_response(resp)
            return (data_dict.get('Tag') for data_dict in service_response.get('data', {})
                    if data_dict.get('Tag'))
        except Exception:
            logger.exception(f'Failed deleting tags {tag_id_list}')
            return []

    def create_tags(self, names_list: Iterable[str], parent_tag_id: Optional[str] = None) \
            -> Tuple[Dict[str, str], Optional[str]]:
        """ see create_tag """

        logger.info(f'Creating tags {names_list} with parent {parent_tag_id}')

        created_tag_ids_by_name = {}  # type: Dict[str, str]
        for tag_name in names_list:
            created_tag_dict = self.create_tag(tag_name, parent_tag_id=parent_tag_id)
            if not created_tag_dict:
                logger.error(f'Tag "{tag_name}" creation failed')
                return created_tag_ids_by_name, tag_name

            created_tag_ids_by_name[tag_name] = created_tag_dict['id']
        return created_tag_ids_by_name, None

    def _prepare_service_request(self,
                                 request_body: Optional[dict] = None,
                                 filter_criteria_list: Optional[Iterable[dict]] = None,
                                 start_offset: Optional[int] = None) -> dict:

        params_dict = {}
        service_request = params_dict.setdefault('ServiceRequest', request_body or {})

        if start_offset:
            service_request['preferences'] = {
                'startFromOffset': start_offset,
                'limitResults': self._devices_per_page
            }

        # handle filters
        criteria_list = []
        if filter_criteria_list:
            criteria_list.extend(filter_criteria_list)

        if self._date_filter:
            # filter by 'last_seen' greater than
            criteria_list.append({
                'field': 'lastVulnScan',
                'operator': 'GREATER',
                'value': self._date_filter,
            })

        if criteria_list:
            service_request.setdefault('filters', {}).setdefault('Criteria', []).extend(criteria_list)

        return params_dict

    @staticmethod
    def _generate_filter_criteria(field: str, operator_name: str, value: str):
        return {'field': field, 'operator': operator_name, 'value': value}

    def _generate_filter_criteria_for_host_ids(self, host_id_list: Iterable[str]):
        return self._generate_filter_criteria('id', 'IN', ','.join(host_id_list))

    @staticmethod
    def _handle_qualys_response(response: bytes):
        service_response = response.get('ServiceResponse')
        response_code = (service_response or {}).get('responseCode')
        if not (service_response and response_code):
            raise RESTException('Malformed response - missing ServiceResponse')
        if response_code != 'SUCCESS':
            raise RESTException(f'failed with code {response_code},'
                                f' message: {(service_response.get("responseErrorDetails") or {}).get("errorMessage")}')
        return service_response
