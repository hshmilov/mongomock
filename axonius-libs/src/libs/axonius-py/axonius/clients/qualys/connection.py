import logging
from typing import List

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
