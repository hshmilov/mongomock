# pylint: disable=import-error
import logging

import pyodbc

logger = logging.getLogger(f'axonius.{__name__}')
TDS_DRIVER = 'FreeTDS'
TDS_VERSION = '8.0'


class MSSQLConnection:
    def __init__(self, database, server, port, devices_paging, tds_version=TDS_VERSION):
        self.database = database
        assert isinstance(port, int), f'the port {port} is not a valid int!'
        self.server = server + ',' + str(port)
        self.devices_paging = devices_paging
        self.username = None
        self.password = None
        self.db = None
        self.tds_version = tds_version

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
        try:
            self.db = pyodbc.connect(server=self.server, user=self.username, password=self.password, driver=TDS_DRIVER,
                                     DATABASE=self.database, tds_version=self.tds_version)
        except Exception as err:
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

    def query(self, sql, *args):
        """
        Performs a database query with connected database.
        :param sql: SQL query
        :return: Array of dictionaries
        """
        self.reconnect()    # Reconnect on every query to ensure a valid-state cursor.
        try:
            cursor = self.db.cursor()
            results = cursor.execute(sql, args)
            columns = [column[0] for column in cursor.description]
            devices_count = 0
            batch = True
            while batch:
                batch = results.fetchmany(self.devices_paging)
                if devices_count < 10 or devices_count % 1000 == 0:
                    logger.info(f'Got {devices_count * self.devices_paging} devices so far')
                devices_count += 1
                for row in batch:
                    yield dict(zip(columns, row))
        except Exception:
            logger.exception('Unable to perform query: ')
            raise

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, _type, value, traceback):
        self.logout()
