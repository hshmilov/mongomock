# pylint: disable=import-error
import logging

from axonius.clients.odbc.connection import ODBCConnection

logger = logging.getLogger(f'axonius.{__name__}')
TDS_DRIVER = 'FreeTDS'
TDS_VERSION = '8.0'


class MSSQLConnection(ODBCConnection):
    def __init__(self, database, server, port, devices_paging, driver=TDS_DRIVER, tds_version=TDS_VERSION):
        assert isinstance(port, int), f'the port {port} is not a valid int!'
        server = server + ',' + str(port)
        super().__init__(database=database,
                         server=server,
                         devices_paging=devices_paging,
                         driver=driver,
                         driver_version=tds_version)
