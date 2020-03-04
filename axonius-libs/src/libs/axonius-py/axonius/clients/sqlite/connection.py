# pylint: disable=import-error
import logging

import sqlite3

from axonius.clients.abstract.abstract_sql_connection import AbstractSQLConnection

logger = logging.getLogger(f'axonius.{__name__}')


class SqliteConnection(AbstractSQLConnection):
    def __init__(self, db_file_path, table_name, devices_paging):
        self.db = None
        self.database = db_file_path
        self.table_name = table_name
        self.devices_paging = devices_paging

    def set_credentials(self, username=None, password=None):
        logger.info('Sqlite credentials is not implemented')

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
            self.db = sqlite3.connect(database=self.database)

            # Trying to fetch 1 row to check connection
            cursor = self.db.cursor()
            cursor.execute(f'select * from {self.table_name} LIMIT 1')
        except Exception as err:
            logger.exception('Connection to SQLite database failed')
            raise ValueError(str(err))

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
        self.reconnect()    # Reconnect on every query to ensure a valid-state cursor.
        try:
            cursor = self.db.cursor()
            results = cursor.execute(sql)
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
            logger.warning('Unable to perform query: ', exc_info=True)
            raise

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, _type, value, traceback):
        self.logout()
