# pylint: disable=import-error
import logging
import pyodbc

from axonius.clients.abstract.abstract_sql_connection import AbstractSQLConnection
from axonius.multiprocess.utils import get_function_rv_safe

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class ODBCConnection(AbstractSQLConnection):
    def __init__(self, database, server, devices_paging, driver, port=None, driver_version=None, use_ntlm_v2='yes'):
        self.database = database
        self.server = server
        # Server may contain port in format 'server,port' therefore may be None
        assert isinstance(port, (int, type(None))), f'the port {port} is not a valid int!'
        self.port = port
        self.devices_paging = devices_paging

        self.driver = driver
        self.driver_version = driver_version
        self.use_ntlm_v2 = use_ntlm_v2

        self.db = None
        self.username = None
        self.password = None

    def set_credentials(self, username, password):
        """ Set the connection credentials

        :param str username: The username
        :param str password: The password
        """
        self.username = username
        self.password = password

    def set_devices_paging(self, devices_paging: int):
        self.devices_paging = devices_paging

    def reconnect(self):
        try:
            self.logout()
        except Exception:
            pass

        self.connect()

    def connect(self):
        """ Connects to the service """
        if not self.username or not self.password:
            raise ValueError('No username or password')

        try:
            self.db = get_function_rv_safe(pyodbc.connect, server=self.server, port=self.port, DATABASE=self.database,
                                           user=self.username, password=self.password, driver=self.driver,
                                           tds_version=self.driver_version, UseNTLMv2=self.use_ntlm_v2)
        except Exception:
            logger.exception('Connection to database failed')
            raise

    def __del__(self):
        self.close()

    def logout(self):
        self.close()

    def close(self):
        """ Closes the connection """
        try:
            self.db.close()
        except Exception:
            pass
        self.db = None

    def query(self, sql: str):
        """
        Performs a database query with connected database.
        :param sql: SQL query
        :return: Array of dictionaries
        """
        logger.info(f'SQL query: {sql}')
        self.reconnect()  # Reconnect on every query to ensure a valid-state cursor.
        try:
            cursor = self.db.cursor()
            results = cursor.execute(sql)
            columns = [column[0] for column in cursor.description]
            entities_count = 0
            batch = True

            if self.devices_paging >= 200:
                log_pages_rate = 100
            else:
                log_pages_rate = 1000

            while batch:
                batch = results.fetchmany(self.devices_paging)
                if entities_count % (self.devices_paging * log_pages_rate) == 0:
                    logger.info(f'Got {entities_count} entities so far')
                entities_count += self.devices_paging
                for row in batch:
                    yield dict(zip(columns, row))

            logger.info(f'Finished with {entities_count}')
        except Exception:
            logger.warning('Unable to perform query: ', exc_info=True)
            raise

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, _type, value, traceback):
        self.logout()
