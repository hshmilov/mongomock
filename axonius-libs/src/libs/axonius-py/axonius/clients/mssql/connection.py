import logging
logger = logging.getLogger(f"axonius.{__name__}")
import pyodbc

from axonius.adapter_exceptions import ClientConnectionAlreadyConnected

TDS_DRIVER = 'FreeTDS'
TDS_VERSION = "8.0"


class MSSQLConnection(object):
    def __init__(self, database, server, port, devices_paging, tds_version=TDS_VERSION):
        self.database = database
        assert type(port) == int, "the port {self.port} is not a valid int!"
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

    @property
    def is_connected(self):
        return self.db is not None

    def connect(self):
        """ Connects to the service """
        if self.is_connected:
            raise ClientConnectionAlreadyConnected()
        try:
            self.db = pyodbc.connect(server=self.server, user=self.username, password=self.password, driver=TDS_DRIVER,
                                     DATABASE=self.database, tds_version=self.tds_version)
        except Exception as err:
            logger.exception("Connection to database failed")
            raise

    def __del__(self):
        self.close()

    def logout(self):
        self.close()

    def close(self):
        """ Closes the connection """
        if self.is_connected:
            try:
                self.db.close()
                self.db = None
            except Exception:
                pass

    def query(self, sql, *args):
        """
        Performs a database query with connected database.
        :param sql: SQL query
        :return: Array of dictionaries
        """
        try:
            cursor = self.db.cursor()
            results = cursor.execute(sql, args)
            columns = [column[0] for column in cursor.description]
            devices_count = 0
            batch = True
            while batch:
                batch = results.fetchmany(self.devices_paging)
                logger.info(f"Got {devices_count*self.devices_paging} devices so far")
                devices_count += 1
                for row in batch:
                    yield dict(zip(columns, row))
        except Exception:
            logger.exception("Unable to perform query: ")
            raise

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.logout()
