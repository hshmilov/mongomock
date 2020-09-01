# pylint: disable=import-error
import logging
from typing import Iterator

import mysql.connector

from axonius.clients.abstract.abstract_sql_connection import AbstractSQLConnection

logger = logging.getLogger(f'axonius.{__name__}')
DEFAULT_PAGINATION = 1000


class MySQLConnection(AbstractSQLConnection):
    def __init__(self, host, port, username, password, db_name):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.db_name = db_name
        self.db = None
        self.devices_paging = DEFAULT_PAGINATION

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
            self.db = mysql.connector.connect(
                user=self.username,
                password=self.password,
                host=self.host,
                port=self.port,
                database=self.db_name
            )
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

    # pylint: disable=too-many-nested-blocks
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
                if len(batch) == 1:
                    # There is a bug in which cursor.fetchmany() returns the same 1 element over and over in an
                    # infinite loop instead of returning []. It happens at the end, when everything was finished.
                    # cursor.fetchone() on the otherhand raises an exception if we reached the end.
                    # Handle it
                    try:
                        result = cursor.fetchone()
                        if result:
                            batch.append(result)
                        else:
                            break
                    except Exception:
                        break
                total_devices += len(batch)
                if sql_pages % 10000 == 1:
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

    # Equivalent to SQL left join.
    @staticmethod
    def left_join_tables(left_table: Iterator[dict],
                         right_table: Iterator[dict],
                         left_comparison_field: str,
                         right_comparison_field: str
                         ):
        # Convert the right table to dict (for fast lookup purpose)
        right_table = {row.get(right_comparison_field): row for row in right_table}

        for row in left_table:
            field_value = row.get(left_comparison_field)
            right_object = right_table.get(field_value) or {}

            for field in right_object:
                row[field] = right_object.get(field)

            yield row

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, _type, value, traceback):
        self.close()
