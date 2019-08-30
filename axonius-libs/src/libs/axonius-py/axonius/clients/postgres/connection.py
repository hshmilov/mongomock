import logging

import psycopg2


logger = logging.getLogger(f'axonius.{__name__}')
DEFAULT_PAGINATION = 1000


class PostgresConnection:
    def __init__(self, host, port, username, password, db_name):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.db_name = db_name
        self.db = None

        assert isinstance(port, int), f'the port {port} is not a valid int!'

    def reconnect(self):
        try:
            self.close()
        except Exception:
            pass

        self.connect()

    def connect(self):
        """ Connects to the service """
        try:
            self.db = psycopg2.connect(
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

    def query(self, sql: str, pagination: int = DEFAULT_PAGINATION):
        """
        Performs a database query with connected database.
        :param sql: SQL query
        :param pagination: pagination
        :return: Array of dictionaries
        """
        self.reconnect()    # Reconnect on every query to ensure a valid-state cursor.
        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            columns = [column[0] for column in cursor.description]
            sql_pages = 0
            total_devices = 0
            batch = True
            while batch:
                batch = cursor.fetchmany(pagination)
                total_devices += len(batch)
                if sql_pages % 10 == 1:
                    logger.info(f'Got {total_devices} devices so far')
                sql_pages += 1
                for row in batch:
                    yield dict(zip(columns, row))
        except Exception:
            logger.exception('Unable to perform query: ')
            raise

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, _type, value, traceback):
        self.close()
