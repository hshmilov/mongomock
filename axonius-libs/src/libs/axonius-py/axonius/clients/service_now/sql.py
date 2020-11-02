import logging

from typing import Optional, Generator, Tuple, Dict

from axonius.clients.mssql.connection import MSSQLConnection
from axonius.clients.service_now import consts
from axonius.clients.service_now.base import ServiceNowConnectionMixin

logger = logging.getLogger(f'axonius.{__name__}')


class ServiceNowMSSQLConnection(MSSQLConnection, ServiceNowConnectionMixin):

    __init__ = MSSQLConnection.__init__
    connect = MSSQLConnection.connect

    get_device_list = ServiceNowConnectionMixin.get_device_list
    get_user_list = ServiceNowConnectionMixin.get_user_list

    def _get_subtables_by_key(self, subtables_key_to_name: dict,
                              additional_params_by_table_key: Optional[dict] = None,
                              parallel_requests: int = consts.DEFAULT_ASYNC_CHUNK_SIZE):
        # ServiceNow MSSQL doesnt support subtables for now
        return {}

    #pylint: disable=arguments-differ
    def _iter_table_results_by_key(self, subtables_key_to_name: Dict[str, str],
                                   additional_params_by_table_key: Optional[dict] = None,
                                   parallel_requests: int = consts.DEFAULT_ASYNC_CHUNK_SIZE) \
            -> Generator[Tuple[str, dict], None, None]:
        self.set_devices_paging(parallel_requests)
        for device_type, table_name in subtables_key_to_name.items():
            try:
                for table_result in self.query(f'Select * from dbo.{table_name}'):
                    table_result = {k: v for k, v in table_result.items() if v != 'NULL'}
                    yield device_type, table_result
            except Exception as e:
                logger.exception(f'Failed querying table dbo.{table_name}: {str(e)}')
