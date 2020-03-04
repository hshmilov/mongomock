import logging

from axonius.utils.sql import SQLDatabases, MySqlAdapter
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.sqlite.connection import SqliteConnection
from axonius.clients.sql.sql_generic import _sql_parse_raw_data
from axonius.mixins.configurable import Configurable
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.consts import remote_file_consts
from axonius.utils.remote_file_utils import load_remote_binary_data, test_file_reachability
from sqlite_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class SqliteAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(MySqlAdapter):
        file_name = Field(str, 'File Name')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return test_file_reachability(client_config)

    # pylint: disable=logging-format-interpolation
    def _connect_client(self, client_config):
        try:
            sqlite_data = load_remote_binary_data(client_config)
            with open(client_config['user_id'], 'wb') as f:
                if not sqlite_data:
                    raise ClientConnectionException(f'Error: empty DB file. Please check the uploaded file')
                f.write(sqlite_data)
            connection = SqliteConnection(
                db_file_path=client_config['user_id'],
                table_name=client_config['table'],
                devices_paging=self.__devices_fetched_at_a_time)
            with connection:
                pass  # check that the connection is valid
            return connection, client_config, SQLDatabases.SQLite.value
        except Exception as err:
            logger.exception(f'Error connecting to sqlite database')
            raise ClientConnectionException(f'Failed connecting to sqlite database. {str(err)}')

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        connection, client_config, sql_type = client_data
        table = client_config['table']
        connection.set_devices_paging(self.__devices_fetched_at_a_time)
        with connection:
            for device_raw in connection.query(f'Select * from {table}'):
                yield device_raw, client_config, sql_type

    @staticmethod
    def _clients_schema():
        """
        The schema Sqlite expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'table',
                    'title': 'SQL Server Table Name',
                    'type': 'string'
                },
                {
                    'name': 'server_tag',
                    'title': 'Server Tag',
                    'type': 'string'
                },
                *remote_file_consts.FILE_CLIENTS_SCHEMA
            ],
            'required': [
                'table',
                *remote_file_consts.FILE_SCHEMA_REQUIRED
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        yield from _sql_parse_raw_data(self._new_device_adapter, devices_raw_data)

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'devices_fetched_at_a_time',
                    'type': 'integer',
                    'title': 'SQL pagination'
                }
            ],
            'required': ['devices_fetched_at_a_time'],
            'pretty_name': 'SQL Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'devices_fetched_at_a_time': 1000
        }

    def _on_config_update(self, config):
        self.__devices_fetched_at_a_time = config['devices_fetched_at_a_time']
