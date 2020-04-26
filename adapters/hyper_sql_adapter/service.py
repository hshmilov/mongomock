import socket
import logging

from typing import Tuple

from axonius.utils.sql import SQLServers, MySqlAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import get_exception_string
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.clients.sql.sql_generic import _sql_parse_raw_data
from axonius.adapter_exceptions import ClientConnectionException
from axonius.mixins.configurable import Configurable
from hyper_sql_adapter.client_id import get_client_id
from hyper_sql_adapter.connection import HyperSQLConnection
from hyper_sql_adapter.consts import DEFAULT_HYPER_SQL_PORT, DEVICES_FETECHED_AT_A_TIME, DRIVER, VALIDATE_TIMEOUT

logger = logging.getLogger(f'axonius.{__name__}')


class HyperSqlAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(MySqlAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__))

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        try:
            sock = socket.create_connection((client_config['domain'], client_config['port']), VALIDATE_TIMEOUT)
            sock.close()
        except Exception as e:
            logger.exception('Test reachability exception')
            return False
        return True

    def get_connection(self, client_config):
        connection = HyperSQLConnection(database=client_config.get('database'),
                                        server=client_config.get('domain'),
                                        port=client_config.get('port'),
                                        devices_paging=self.__devices_fetched_at_a_time,
                                        driver=DRIVER)

        connection.set_credentials(username=client_config.get('username'),
                                   password=client_config.get('password'))
        with connection:
            pass  # check that the connection credentials are valid
        return connection, client_config, SQLServers.HyperSQL.value

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except Exception:
            message = f'Error connecting to client host: {client_config.get("domain")}  ' \
                      f'database: ' \
                      f'{client_config.get("database")}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string())

    def _query_devices_by_client(self, client_name, client_data: Tuple[HyperSQLConnection, dict, str]):
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
        The schema HyperSqlAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'HSQL Server Host',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'Port',
                    'type': 'integer',
                    'default': DEFAULT_HYPER_SQL_PORT,
                    'format': 'port'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'database',
                    'title': 'HSQL Server Database Name',
                    'type': 'string',
                },
                {
                    'name': 'table',
                    'title': 'HSQL Server Table Name',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'port',
                'database',
                'table'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
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
            'pretty_name': 'HyperSql Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'devices_fetched_at_a_time': DEVICES_FETECHED_AT_A_TIME
        }

    def _on_config_update(self, config):
        self.__devices_fetched_at_a_time = config['devices_fetched_at_a_time']
