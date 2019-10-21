# pylint: disable=import-error
import logging
import cx_Oracle

from axonius.clients.abstract.abstract_sql_connection import AbstractSQLConnection

logger = logging.getLogger(f'axonius.{__name__}')
DEFAULT_PAGINATION = 1000


class OracleDBConnection(AbstractSQLConnection):
    def __init__(self, host, port, username, password, service, devices_paging=DEFAULT_PAGINATION):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.db = None
        self.devices_paging = devices_paging
        self.service = service

        assert isinstance(port, int), f'the port {port} is not a valid int!'

    def set_credentials(self, username, password):
        self.username = username
        self.password = password

    def set_devices_paging(self, devices_paging: int):
        self.devices_paging = devices_paging

    def reconnect(self):
        try:
            self.close()
        except Exception:
            pass

        self.connect()

    def connect(self):
        """ Connects to the service """
        try:
            self.db = cx_Oracle.connect(f'{self.username}/{self.password}@{self.host}:{self.port}/{self.service}')
        except Exception:
            logger.exception('Connection to database failed')
            raise

    def __del__(self):
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
        :param pagination: pagination
        :return: Array of dictionaries
        """
        self.reconnect()    # Reconnect on every query to ensure a valid-state cursor.
        cursor = self.db.cursor()
        try:
            cursor.execute(sql)
            columns = [column[0] for column in cursor.description]
            sql_pages = 0
            total_devices = 0
            batch = True
            while batch:
                batch = cursor.fetchmany(self.devices_paging)
                total_devices += len(batch)
                if sql_pages % 10 == 1:
                    logger.info(f'Got {total_devices} devices so far')
                sql_pages += 1
                for row in batch:
                    yield dict(zip(columns, row))
        except Exception:
            logger.exception('Unable to perform query: ')
            raise
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, _type, value, traceback):
        self.close()
