import logging

from axonius.clients.odbc.connection import ODBCConnection

logger = logging.getLogger(f'axonius.{__name__}')


class HyperSQLConnection(ODBCConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
