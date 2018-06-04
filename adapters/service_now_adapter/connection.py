import logging
logger = logging.getLogger(f"axonius.{__name__}")
from service_now_adapter.consts import *
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException


class ServiceNowConnection(RESTConnection):
    def __init__(self, number_of_offsets, offset_size, *args, **kwargs):
        """ Initializes a connection to ServiceNow using its rest API

        """
        super().__init__(*args, **kwargs)
        self.__number_of_offsets = number_of_offsets
        self.__offset_size = offset_size

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

    def create_incident(self):
        self.__add_dict_to_table("incident", {})
