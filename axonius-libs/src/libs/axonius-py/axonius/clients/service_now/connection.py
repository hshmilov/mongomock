import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.clients.service_now.consts import *
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.consts import report_consts
from axonius.clients.service_now import consts


class ServiceNowConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        """ Initializes a connection to ServiceNow using its rest API

        """
        self.__number_of_offsets = consts.NUMBER_OF_OFFSETS
        self.__offset_size = consts.OFFSET_SIZE
        self._headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        self._url_base_prefix = "api/now/"
        super().__init__(*args, **kwargs)

    def _connect(self):
        if self._username is not None and self._password is not None:
            self._get("table/cmdb_ci_computer", url_params={"sysparm_limit": 1}, do_basic_auth=True)
        else:
            raise RESTException("No user name or password")

    def get_device_list(self):
        tables_devices = []
        for table_details in TABLES_DETAILS:
            new_table_details = table_details.copy()
            table_devices = {DEVICES_KEY: self.__get_devices_from_table(table_details[TABLE_NAME_KEY])}
            new_table_details.update(table_devices)
            tables_devices.append(new_table_details)
        return tables_devices

    def __get_devices_from_table(self, table_name):
        for sysparm_offset in range(0, self.__number_of_offsets):
            try:
                table_results_paged = self._get(f"table/{str(table_name)}", url_params={"sysparm_limit":
                                                                                        self.__offset_size,
                                                                                        "sysparm_offset": sysparm_offset * self.__offset_size})
                if len(table_results_paged.get("result", [])) == 0:
                    break
                yield from table_results_paged.get("result", [])
            except Exception:
                logger.exception(f"Got exception in offset {sysparm_offset} with table {table_name}")
                break

    def __add_dict_to_table(self, table_name, dict_data):
        self._post(f"table/{str(table_name)}", body_params=dict_data)

    def create_service_now_incident(self, service_now_dict):
        impact = service_now_dict.get('impact', report_consts.SERVICE_NOW_SEVERITY['error'])
        short_description = service_now_dict.get('short_description', "")
        description = service_now_dict.get('description', "")
        try:
            self.__add_dict_to_table('incident', {'impact': impact, 'urgency': impact,
                                                  'short_description': short_description, 'description': description})
            return True
        except Exception:
            return False

    def create_service_now_computer(self, connection_dict):

        try:
            self.__add_dict_to_table('cmdb_ci_computer', connection_dict)
            return True
        except Exception:
            return False
