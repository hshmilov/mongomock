import io
import json
import logging
from math import ceil
from typing import Generator, Tuple, List, Optional
from aiohttp import ClientResponse

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.service_now import consts
from axonius.consts import report_consts

logger = logging.getLogger(f'axonius.{__name__}')


class ServiceNowConnection(RESTConnection):
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

    def _upload_csv_to_table(self, table_name, table_sys_id, csv_string):
        csv_bytes = io.BytesIO(csv_string.encode('utf-8'))
        self._post('attachment/file',
                   url_params={'table_name': table_name,
                               'table_sys_id': table_sys_id,
                               'file_name': 'report.csv'},
                   files_param={'file': ('report.csv', csv_bytes, 'text/csv', {'Expires': '0'})},
                   extra_headers={'Content-Type': None})

    def get_user_list(self):

        # prepare users dict by sys_id
        users_table_dict = dict()
        # Note: we only have a single table so we ignore the returned table_key
        for _, users_chunk in self._iter_async_table_chunks_by_key({consts.USERS_TABLE_KEY: consts.USERS_TABLE}):
            for user in users_chunk:
                if user.get('sys_id'):
                    users_table_dict[user.get('sys_id')] = user

        for user in users_table_dict.values():
            user_to_yield = user.copy()
            try:
                if (user.get('manager') or {}).get('value'):
                    user_to_yield['manager_full'] = users_table_dict.get(user.get('manager').get('value'))
            except Exception:
                logger.exception(f'Problem getting manager for user {user}')
            yield user_to_yield

    # pylint: disable=arguments-differ
    def get_device_list(self, fetch_users_info_for_devices=False, fetch_ci_relations=False):
        subtables_by_key = self._get_subtables_by_key(fetch_users_info_for_devices=fetch_users_info_for_devices,
                                                      fetch_ci_relations=fetch_ci_relations)
        self.__users_table = subtables_by_key.get(consts.USERS_TABLE_KEY) or {}
        for device_type, table_name, table_chunk in self.__iter_device_table_chunks_by_details():
            yield {
                consts.TABLE_NAME_KEY: table_name,
                consts.DEVICE_TYPE_NAME_KEY: device_type,
                consts.DEVICES_KEY: table_chunk,
                # Inject subtables to every table chunk
                # Note: '**' operator expands the dict into its individual items for addition in the new one.
                **subtables_by_key,
            }

    @staticmethod
    def _prepare_relations_fields():
        fields = ['type.name']
        for relation in [consts.RELATIONS_TABLE_CHILD_KEY, consts.RELATIONS_TABLE_PARENT_KEY]:
            for relative_field in ['sys_id', 'sys_class_name', 'name']:
                fields.append(f'{relation}.{relative_field}')
        return ','.join(fields)

    @staticmethod
    def _prepare_relative_dict(relation_dict, relation):
        """ relation = RELATIONS_TABLE_CHILD_KEY | RELATIONS_TABLE_PARENT_KEY  """
        return {k.replace(f'{relation}.', '', 1): v
                for k, v in relation_dict.items()
                if (isinstance(k, str) and k.startswith(f'{relation}.'))}

    # pylint: disable=too-many-branches,too-many-statements
    def _get_subtables_by_key(self, fetch_users_info_for_devices=False, fetch_ci_relations=False):
        tables_by_key = {}

        sub_tables_to_request_by_key = consts.DEVICE_SUB_TABLES_KEY_TO_NAME.copy()
        # if users were not requested, dont fetch them
        if not fetch_users_info_for_devices:
            tables_by_key.setdefault(consts.USERS_TABLE_KEY, dict())
            del sub_tables_to_request_by_key[consts.USERS_TABLE_KEY]

        additional_url_params_by_table_key = {}
        if fetch_ci_relations:
            additional_url_params_by_table_key = {
                consts.RELATIONS_TABLE: {'sysparm_fields': self._prepare_relations_fields()},
            }
        else:
            # if relations were not requested, dont fetch them
            tables_by_key.setdefault(consts.RELATIONS_TABLE, dict())
            del sub_tables_to_request_by_key[consts.RELATIONS_TABLE]

        for table_key, table_results_chunk in self._iter_async_table_chunks_by_key(
                sub_tables_to_request_by_key, additional_params_by_table_key=additional_url_params_by_table_key):
            # Note: all checks for validity of table_results_chunk are performed by the generator
            for sub_table_result in table_results_chunk:
                if not isinstance(sub_table_result, dict):
                    logger.warning(f'Invalid table_result received for key {table_key}: {sub_table_result}')
                    continue

                curr_table = tables_by_key.setdefault(table_key, dict())

                # General subtable cases - table = {'sys_id': general subtable dict}
                if table_key in [consts.USERS_TABLE_KEY, consts.LOCATION_TABLE_KEY,
                                 consts.USER_GROUPS_TABLE_KEY, consts.DEPARTMENT_TABLE_KEY,
                                 consts.ALM_ASSET_TABLE, consts.COMPANY_TABLE, consts.U_SUPPLIER_TABLE,
                                 consts.MAINTENANCE_SCHED_TABLE, consts.SOFTWARE_PRODUCT_TABLE, consts.MODEL_TABLE]:
                    sys_id = sub_table_result.get('sys_id')
                    if not sys_id:
                        continue
                    if sys_id in curr_table:
                        logger.debug(f'Located sys_id duplication "{sys_id}" in sub_table_key {table_key}')
                        continue
                    curr_table[sys_id] = sub_table_result

                    # ADDITIONALLY, for users table key, configure username subtable as well
                    if table_key == consts.USERS_TABLE_KEY:
                        # Note: the check for 'name' vs the usage of 'user_name' was on the original sync impl.
                        username = sub_table_result.get('user_name')
                        if not (sub_table_result.get('name') and username):
                            continue
                        username_subtable = tables_by_key.setdefault(consts.USERS_USERNAME_KEY, dict())
                        if username in username_subtable:
                            logger.debug(f'Located username duplication "{username}" in sub_table_key {table_key}')
                            continue
                        username_subtable[username] = sub_table_result.get('sys_id')

                # CI_IPS - table = {'nic_dict.u_nic': [nic dicts...]}
                elif table_key == consts.CI_IPS_TABLE:
                    if not sub_table_result.get('asset'):
                        continue
                    curr_table.setdefault(sub_table_result.get('u_nic'), list()).append(sub_table_result)

                # IPS - curr_table = {'ip_dict.u_configuration_item.value': [ips dicts...]}
                elif table_key == consts.IPS_TABLE:
                    configuration_item_value = (sub_table_result.get('u_configuration_item') or {}).get('value')
                    if not configuration_item_value:
                        continue
                    curr_table.setdefault(configuration_item_value, list()).append(sub_table_result)

                # NIC - curr_table = {'nic_dict.cmdb_ci.value': [nic dicts...]}
                elif table_key == consts.NIC_TABLE_KEY:
                    cmdb_ci_value = (sub_table_result.get('cmdb_ci') or {}).get('value')
                    if not cmdb_ci_value:
                        continue
                    curr_table.setdefault(cmdb_ci_value, list()).append(sub_table_result)

                # Relations - curr_table = {'sys_id': {RELATIONS_PARENT: ['sys_id', ...],
                #                                      RELATIONS_CHILD: ['sys_id', ...]}
                elif table_key == consts.RELATIONS_TABLE:
                    parent_sys_id = sub_table_result.pop(f'{consts.RELATIONS_TABLE_PARENT_KEY}.sys_id', None)
                    child_sys_id = sub_table_result.pop(f'{consts.RELATIONS_TABLE_CHILD_KEY}.sys_id', None)
                    if not (parent_sys_id and child_sys_id):
                        continue

                    # Mark: parent -child> child
                    parent_relations = curr_table.setdefault(parent_sys_id, {})
                    parent_relations.setdefault(consts.RELATIONS_TABLE_CHILD_KEY, set()).add(child_sys_id)

                    # Mark: parent <-parent- child
                    child_relations = curr_table.setdefault(child_sys_id, {})
                    child_relations.setdefault(consts.RELATIONS_TABLE_PARENT_KEY, set()).add(parent_sys_id)

                    # prepare relatives information - {'sys_id': {'name': name, 'sys_class_name': class_name}}
                    relations_details = tables_by_key.setdefault(consts.RELATIONS_DETAILS_TABLE_KEY, dict())

                    # save parent details
                    if parent_sys_id not in relations_details:
                        relations_details[parent_sys_id] = self._prepare_relative_dict(
                            sub_table_result, consts.RELATIONS_TABLE_PARENT_KEY)

                    # save child details
                    if child_sys_id not in relations_details:
                        relations_details[child_sys_id] = self._prepare_relative_dict(
                            sub_table_result, consts.RELATIONS_TABLE_CHILD_KEY)

                else:
                    logger.error('Invalid sub_table_key encountered {sub_table_key}')
                    continue

        return tables_by_key

    @staticmethod
    def __get_table_name_by_device_type():
        return {table_details[consts.DEVICE_TYPE_NAME_KEY]: table_details[consts.TABLE_NAME_KEY]
                for table_details in consts.TABLES_DETAILS}

    def __iter_device_table_chunks_by_details(self) -> Generator[Tuple[str, str, List[dict]], None, None]:
        # prepare table_name_by_key for async requests
        table_name_by_device_type = self.__get_table_name_by_device_type()
        for device_type, table_results_chunk in self._iter_async_table_chunks_by_key(table_name_by_device_type):
            # Note: all checks for validity of table_results_chunk are performed by the generator
            yield (device_type, table_name_by_device_type[device_type], table_results_chunk)

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
                                        additional_params_by_table_key: Optional[dict] = None) \
            -> Generator[Tuple[str, dict], None, None]:
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
                                                           retry_on_error=True)):
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
                                                                   chunks=consts.ASYNC_CHUNK_SIZE)):
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
        cmdb_ci_table = connection_dict.get('cmdb_ci_table') or 'cmdb_ci_computer'
        logger.info(f'Creating service now computer ')
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
