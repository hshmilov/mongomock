import io
import json
import logging
from math import ceil
from typing import Generator, Tuple, List, Optional, Dict
from aiohttp import ClientResponse

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.service_now import consts
from axonius.clients.service_now.base import ServiceNowConnectionMixin
from axonius.consts import report_consts

logger = logging.getLogger(f'axonius.{__name__}')


class ServiceNowConnection(RESTConnection, ServiceNowConnectionMixin):
    def __init__(self, *args, **kwargs):
        """ Initializes a connection to ServiceNow using its rest API

        """
        self.__users_table = dict()
        self.__number_of_offsets = consts.NUMBER_OF_OFFSETS
        self.__offset_size = consts.OFFSET_SIZE
        super().__init__(url_base_prefix='api/now/', *args, **kwargs)
        self._permanent_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    def _connect(self):
        if self._username is not None and self._password is not None:
            self._get('table/cmdb_ci_computer', url_params={'sysparm_limit': 1}, do_basic_auth=True)
        else:
            raise RESTException('No user name or password')

    get_device_list = ServiceNowConnectionMixin.get_device_list
    get_user_list = ServiceNowConnectionMixin.get_user_list

    def _upload_csv_to_table(self, table_name, table_sys_id, csv_string):
        csv_bytes = io.BytesIO(csv_string.encode('utf-8'))
        self._post('attachment/file',
                   url_params={'table_name': table_name,
                               'table_sys_id': table_sys_id,
                               'file_name': 'report.csv'},
                   files_param={'file': ('report.csv', csv_bytes, 'text/csv', {'Expires': '0'})},
                   extra_headers={'Content-Type': None})

    def _iter_table_results_by_key(self, subtables_key_to_name: Dict[str, str],
                                   additional_params_by_table_key: Optional[dict] = None,
                                   parallel_requests: int = consts.DEFAULT_ASYNC_CHUNK_SIZE) \
            -> Generator[Tuple[str, dict], None, None]:
        for table_key, table_results_chunk in self._iter_async_table_chunks_by_key(
                table_name_by_key=subtables_key_to_name,
                additional_params_by_table_key=additional_params_by_table_key,
                async_chunks=parallel_requests):

            for table_result in table_results_chunk:
                yield table_key, table_result

    @staticmethod
    def _get_table_async_request_params(table_name: str, offset: int, page_size: int,
                                        additional_url_params: Optional[dict]=None):
        if not additional_url_params:
            additional_url_params = dict()
        sysparm_query = 'ORDERBYDESCsys_created_on'
        additional_query = additional_url_params.get('sysparm_query')
        if isinstance(additional_query, str):
            # Note: ^ == AND
            sysparm_query = f'{sysparm_query}^{additional_query}'
        return {'name': f'table/{str(table_name)}',
                'do_basic_auth': True,
                # See: https://hi.service-now.com/kb_view.do?sysparm_article=KB0727636
                'url_params': {'sysparm_limit': page_size,
                               'sysparm_offset': offset,
                               'sysparm_query': sysparm_query,
                               **additional_url_params}}

    def _iter_async_table_chunks_by_key(self, table_name_by_key: dict,
                                        additional_params_by_table_key: Optional[dict] = None,
                                        async_chunks: int = consts.DEFAULT_ASYNC_CHUNK_SIZE) \
            -> Generator[Tuple[str, List[dict]], None, None]:
        """ yields table chunks in the form of (table_key, List[table_result_dict]) tuple.
            When pagination has stopped for a specific table_key, it yields a last (table_key, None)"""

        if not additional_params_by_table_key:
            additional_params_by_table_key = dict()

        # prepare initial request for each table
        # Note: these requests are only to retrieve the total count
        initial_request_params_by_key = {
            table_key: {
                **self._get_table_async_request_params(
                    table_name, 0, 1, additional_url_params=additional_params_by_table_key.get(table_key)),
                # Note: Initial requests needs to return in raw form to read its headers
                'return_response_raw': True,
            } for table_key, table_name in table_name_by_key.items()}

        # run the initial requests to retrieve the total count (ignore first page results)
        table_total_counts_by_key = {}
        for table_key, raw_response in zip(initial_request_params_by_key.keys(),
                                           self._async_get(list(initial_request_params_by_key.values()),
                                                           retry_on_error=True, chunks=async_chunks)):
            if not (self._is_async_response_good(raw_response) and isinstance(raw_response, ClientResponse)):
                logger.warning(f'Async response returned bad, its {raw_response}')
                continue

            try:
                table_total_counts_by_key[table_key] = int(raw_response.headers['X-Total-Count'])
            except Exception:
                logger.warning(f'Unable to retrieve totals for table_key {table_key}.')
                continue
        logger.info(f'Requested counts: {table_total_counts_by_key}')

        # prepare requests for all table pages whose total we achieved successfully
        table_keys = []
        chunk_requests = []
        for table_key, total_count in table_total_counts_by_key.items():
            # compute page count
            number_of_offsets = min(ceil(total_count / float(self.__offset_size)),
                                    self.__number_of_offsets)
            table_name = table_name_by_key[table_key]
            for page_offset in range(0, number_of_offsets):
                table_keys.append(table_key)
                offset = page_offset * self.__offset_size
                chunk_requests.append(self._get_table_async_request_params(
                    table_name, offset, self.__offset_size,
                    additional_url_params=additional_params_by_table_key.get(table_key)))

        # run all the async requests
        for table_key, response in zip(table_keys, self._async_get(chunk_requests, retry_on_error=True,
                                                                   chunks=async_chunks)):
            table_results_chunk = self.__parse_results_chunk_from_response(response, table_key)
            # Note: Invalid response and data validity in response are audited and checked in the parse method
            if not table_results_chunk:
                continue

            logger.debug(f'yielding {len(table_results_chunk)} results for table_key {table_key}')
            yield table_key, table_results_chunk

    def __parse_results_chunk_from_response(self, response, table_key):

        if not self._is_async_response_good(response):
            logger.error(f'Async response returned bad, its {response}')
            return None

        if not isinstance(response, dict):
            logger.warning(f'Invalid response returned: {response}')
            return None

        table_results_chunk = response.get('result', [])
        if not isinstance(table_results_chunk, list):
            logger.warning(f'Invalid result returned for table_key {table_key}: {table_results_chunk}')
            return None

        curr_count = len(table_results_chunk)
        if curr_count == 0:
            logger.info(f'No results returned for table_key {table_key}')
            return None

        return table_results_chunk

    def __get_devices_from_table(self, table_name, number_of_offsets=None):
        logger.info(f'Fetching table {table_name}')
        if not number_of_offsets:
            number_of_offsets = self.__number_of_offsets
        number_of_exception = 0
        for sysparam_offset in range(0, number_of_offsets):
            try:
                table_results_paged = self._get(f'table/{str(table_name)}', do_basic_auth=True,
                                                url_params={'sysparm_limit': self.__offset_size,
                                                            'sysparm_offset': sysparam_offset * self.__offset_size})
                if len(table_results_paged.get('result', [])) == 0:
                    break
                if sysparam_offset % 20 == 0:
                    logger.info(f'Got to offfset {sysparam_offset}')
                yield from table_results_paged.get('result', [])
            except Exception:
                logger.exception(f'Got exception in offset {sysparam_offset} with table {table_name}')
                number_of_exception += 1
                if number_of_exception >= 3:
                    break

    def __add_dict_to_table(self, table_name, dict_data):
        return self._post(f'table/{str(table_name)}', body_params=dict_data)

    def __update_dict_in_table(self, table_name, sys_id, dict_data):
        self._patch(f'table/{table_name}/{sys_id}', body_params=dict_data)
        return self._get(f'table/{table_name}/{sys_id}')

    # pylint: disable=too-many-branches
    def create_service_now_incident(self, service_now_dict):
        impact = service_now_dict.get('impact', report_consts.SERVICE_NOW_SEVERITY['error'])
        short_description = service_now_dict.get('short_description', '')
        description = service_now_dict.get('description', '')
        u_incident_type = service_now_dict.get('u_incident_type')
        u_requested_for = service_now_dict.get('u_requested_for')
        assignment_group = service_now_dict.get('assignment_group')
        u_symptom = service_now_dict.get('u_symptom')
        cmdb_ci = service_now_dict.get('cmdb_ci')
        caller_id = service_now_dict.get('caller_id')
        category = service_now_dict.get('category')
        subcategory = service_now_dict.get('subcategory')
        csv_string = service_now_dict.get('csv_string')

        logger.info(f'Creating servicenow incident: impact={impact}, '
                    f'short_description={short_description}, description={description}')
        try:
            final_dict = {'impact': impact,
                          'urgency': impact,
                          'short_description': short_description,
                          'description': description}
            if u_incident_type:
                final_dict['u_incident_type'] = u_incident_type
            if u_requested_for:
                final_dict['u_requested_for'] = u_requested_for
            if assignment_group:
                final_dict['assignment_group'] = assignment_group
            if u_symptom:
                final_dict['u_symptom'] = u_symptom
            if cmdb_ci:
                final_dict['cmdb_ci'] = cmdb_ci
            if caller_id:
                final_dict['caller_id'] = caller_id
            if category:
                final_dict['category'] = category
            if subcategory:
                final_dict['subcategory'] = subcategory
            try:
                extra_fields = service_now_dict.get('extra_fields')
                if extra_fields:
                    extra_fields_dict = json.loads(extra_fields)
                    if isinstance(extra_fields_dict, dict):
                        final_dict.update(extra_fields_dict)
            except Exception:
                logger.exception(f'Problem getting additional fields')
            incident_value = self.__add_dict_to_table('incident', final_dict)
            if csv_string and (incident_value.get('result') or {}).get('sys_id'):
                self._upload_csv_to_table(table_name='incident', table_sys_id=incident_value['result']['sys_id'],
                                          csv_string=csv_string)
            return True
        except Exception:
            logger.exception(f'Exception while creating incident')
            return False

    def create_service_now_computer(self, connection_dict):
        identifyreconcile_endpoint = None
        try:
            identifyreconcile_endpoint = connection_dict.pop('identifyreconcile_endpoint', None)
        except Exception:
            pass
        cmdb_ci_table = connection_dict.get('cmdb_ci_table') or 'cmdb_ci_computer'
        logger.info(f'Creating service now computer ')
        if identifyreconcile_endpoint:
            body_params = {'relations': [], 'items': [connection_dict]}
            self._post(f'identifyreconcile',
                       url_params={'sysparm_data_source': identifyreconcile_endpoint},
                       body_params=body_params)
            return True, None
        try:
            device_raw = self.__add_dict_to_table(cmdb_ci_table, connection_dict)['result']
            return True, device_raw
        except Exception:
            logger.exception(f'Exception while creating incident with connection dict {connection_dict}')
            return False, None

    def update_service_now_computer(self, connection_dict):
        cmdb_ci_table = connection_dict['sys_class_name']
        sys_id = connection_dict['sys_id']
        logger.info(f'Updating service now computer')
        try:
            device_raw = self.__update_dict_in_table(cmdb_ci_table, sys_id, connection_dict)['result']
            return True, device_raw
        except Exception:
            logger.exception(f'Exception while creating incident with connection dict {connection_dict}')
            return False, None
