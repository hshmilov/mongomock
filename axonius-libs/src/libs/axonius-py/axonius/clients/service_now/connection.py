import logging

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
        self.__number_of_incidents = 0
        self.__number_of_new_computers = 0

    def _connect(self):
        if self._username is not None and self._password is not None:
            self._get('table/cmdb_ci_computer', url_params={'sysparm_limit': 1}, do_basic_auth=True)
        else:
            raise RESTException('No user name or password')

    def get_user_list(self):
        for user in self.__users_table.values():
            user_to_yield = user.copy()
            try:
                if (user.get('manager') or {}).get('value'):
                    user_to_yield['manager_full'] = self.__users_table.get(user.get('manager').get('value'))
            except Exception:
                logger.exception(f'Problem getting manager for user {user}')
            yield user_to_yield

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    # pylint: disable=arguments-differ
    def get_device_list(self, fetch_users_info_for_devices=False):
        tables_devices = []
        users_table = []
        try:
            if fetch_users_info_for_devices:
                users_table = list(self.__get_devices_from_table(consts.USERS_TABLE))
            else:
                users_table = []
        except Exception:
            logger.exception(f'Problem getting users')

        location_table = []
        try:
            location_table = list(self.__get_devices_from_table(consts.LOCATIONS_TABLE))
        except Exception:
            logger.exception(f'Problem getting location')
        nics_table = []
        try:
            nics_table = list(self.__get_devices_from_table(consts.NIC_TABLE_KEY))
        except Exception:
            logger.exception(f'Problem getting nics')

        departments_table = []
        try:
            departments_table = list(self.__get_devices_from_table(consts.DEPARTMENTS_TABLE))
        except Exception:
            logger.exception(f'Problem getting departments')
        companies_table = []
        try:
            companies_table = list(self.__get_devices_from_table(consts.COMPANY_TABLE))
        except Exception:
            logger.exception(f'Problem getting companies')
        users_table_dict = dict()
        for user in users_table:
            if user.get('sys_id'):
                users_table_dict[user.get('sys_id')] = user

        location_table_dict = dict()
        for location in location_table:
            if location.get('sys_id'):
                location_table_dict[location.get('sys_id')] = location
        try:
            nic_table_dict = dict()
            for nic in nics_table:
                if (nic.get('cmdb_ci') or {}).get('value'):
                    if (nic.get('cmdb_ci') or {}).get('value') not in nic_table_dict:
                        nic_table_dict[(nic.get('cmdb_ci') or {}).get('value')] = []
                    nic_table_dict[(nic.get('cmdb_ci') or {}).get('value')].append(nic)
        except Exception:
            logger.exception(f'Problem building nic dict')
        department_table_dict = dict()
        for department in departments_table:
            if department.get('sys_id'):
                department_table_dict[department.get('sys_id')] = department

        alm_asset_table = []
        try:
            alm_asset_table = list(self.__get_devices_from_table(consts.ALM_ASSET_TABLE))
        except Exception:
            logger.exception(f'Problem getting location')
        alm_asset_table_dict = dict()
        for alm_asset in alm_asset_table:
            if alm_asset.get('sys_id'):
                alm_asset_table_dict[alm_asset.get('sys_id')] = alm_asset

        companies_table_dict = dict()
        for company in companies_table:
            if company.get('sys_id'):
                companies_table_dict[company.get('sys_id')] = company

        self.__users_table = users_table_dict
        for table_details in consts.TABLES_DETAILS:
            new_table_details = table_details.copy()
            table_devices = {consts.DEVICES_KEY: self.__get_devices_from_table(table_details[consts.TABLE_NAME_KEY])}
            new_table_details.update(table_devices)
            new_table_details[consts.USERS_TABLE_KEY] = users_table_dict
            new_table_details[consts.LOCATION_TABLE_KEY] = location_table_dict
            new_table_details[consts.NIC_TABLE_KEY] = nic_table_dict
            new_table_details[consts.DEPARTMENT_TABLE_KEY] = department_table_dict
            new_table_details[consts.ALM_ASSET_TABLE] = alm_asset_table_dict
            new_table_details[consts.COMPANY_TABLE] = companies_table_dict
            tables_devices.append(new_table_details)

        return tables_devices

    def __get_devices_from_table(self, table_name, number_of_offsets=None):
        if not number_of_offsets:
            number_of_offsets = self.__number_of_offsets
        number_of_exception = 0
        for sysparam_offset in range(0, number_of_offsets):
            try:
                table_results_paged = self._get(f'table/{str(table_name)}',
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

        self.__number_of_incidents += 1
        logger.info(f'Creating servicenow incident num {self.__number_of_incidents}: impact={impact}, '
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
            self.__add_dict_to_table('incident', final_dict)
            return True
        except Exception:
            logger.exception(f'Exception while creating incident for num {self.__number_of_incidents}')
            return False

    def create_service_now_computer(self, connection_dict):
        self.__number_of_new_computers += 1
        logger.info(f'Creating service now computer num {self.__number_of_new_computers}')
        try:
            device_raw = self.__add_dict_to_table('cmdb_ci_computer', connection_dict)['result']
            return True, device_raw
        except Exception:
            logger.exception(f'Exception while creating incident for '
                             f'num {self.__number_of_new_computers} with connection dict {connection_dict}')
            return False, None
