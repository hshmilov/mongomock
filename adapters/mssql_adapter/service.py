import logging
import json

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.mssql.connection import MSSQLConnection
from axonius.clients.mysql.connection import MySQLConnection
from axonius.clients.oracle_db.connection import OracleDBConnection
from axonius.clients.postgres.connection import PostgresConnection
from axonius.clients.sql.sql_generic import _sql_parse_raw_data
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.utils.json_encoders import IgnoreErrorJSONEncoder
from axonius.utils.network.sockets import test_reachability_tcp
from axonius.utils.sql import SQLServers, MySqlAdapter, MySqlUserAdapter
from axonius.utils.dynamic_device_mixin import DynamicDeviceMixin
from mssql_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class MssqlAdapter(AdapterBase, Configurable, DynamicDeviceMixin):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(MySqlAdapter):
        pass

    class MyUserAdapter(MySqlUserAdapter):
        pass

    DYNAMIC_FIELD_TITLE_PREFIX = 'MSSQL'

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    def _test_reachability(self, client_config):
        return test_reachability_tcp(
            client_config.get('server'),
            client_config.get('port')
        )

    def _connect_client(self, client_config):
        try:
            # For migration purposes, if database_type is not there, leave it as MSSQL
            db_type = client_config.get('database_type') or SQLServers.MSSQL.value
            self.sql_type = db_type

            if db_type == SQLServers.MSSQL.value:
                connection = MSSQLConnection(database=client_config.get('database'),
                                             server=client_config['domain'],
                                             port=int(client_config.get('port')),
                                             devices_paging=self.__devices_fetched_at_a_time)
            elif db_type == SQLServers.Postgres.value:
                connection = PostgresConnection(
                    client_config['domain'],
                    int(client_config.get('port')),
                    client_config['username'],
                    client_config['password'],
                    client_config.get('database'),
                )
            elif db_type == SQLServers.MySQL.value:
                connection = MySQLConnection(
                    client_config['domain'],
                    int(client_config.get('port')),
                    client_config['username'],
                    client_config['password'],
                    client_config.get('database'),
                )
            elif db_type == SQLServers.Oracle.value:
                connection = OracleDBConnection(
                    client_config['domain'],
                    int(client_config.get('port')),
                    client_config['username'],
                    client_config['password'],
                    client_config.get('database')
                )
            else:
                raise ClientConnectionException(f'Unknown DB Type {db_type}!')

            connection.set_credentials(username=client_config['username'],
                                       password=client_config['password'])
            with connection:
                pass  # check that the connection credentials are valid
            return connection, client_config, db_type
        except Exception as err:
            domain = client_config['domain']
            database = client_config['database']
            message = f'Error connecting to client host: {domain}  ' \
                      f'database: ' \
                      f'{database}'
            logger.exception(message)
            raise ClientConnectionException(f'Failed connecting to {db_type} database. {str(err)}')

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        connection, client_config, sql_type = client_data
        if client_config.get('is_users'):
            return
        table = client_config['table']
        connection.set_devices_paging(self.__devices_fetched_at_a_time)
        with connection:
            devices_raw = list(connection.query(f'Select * from {table}'))
        for device_raw in devices_raw:
            yield device_raw, client_config, sql_type

    # pylint: disable=arguments-differ
    def _query_users_by_client(self, client_name, client_data):
        """
        Get all users from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        connection, client_config, sql_type = client_data
        if not client_config.get('is_users'):
            return
        table = client_config['table']
        connection.set_devices_paging(self.__devices_fetched_at_a_time)
        with connection:
            for user_raw in connection.query(f'Select * from {table}'):
                yield user_raw, client_config, sql_type

    @staticmethod
    def _clients_schema():
        """
        The schema MssqlAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'SQL Server Host',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'SQL Server Port',
                    'type': 'string'
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
                    'title': 'SQL Server Database Name',
                    'type': 'string'
                },
                {
                    'name': 'table',
                    'title': 'SQL Server Table Name',
                    'type': 'string'
                },
                {
                    'name': 'database_type',
                    'title': 'Database Type',
                    'type': 'string',
                    'enum': [db_type.value for db_type in SQLServers]
                },
                {
                    'name': 'is_users',
                    'title': 'Is Users Table',
                    'type': 'bool',
                    'default': False
                },
                {
                    'name': 'server_tag',
                    'title': 'Server Tag',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'port',
                'database',
                'table',
                'database_type',
                'is_users'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        yield from _sql_parse_raw_data(self._new_device_adapter, devices_raw_data)

    # pylint: disable=logging-format-interpolation
    def _create_user(self, user_raw, client_config):
        try:
            user = self._new_user_adapter()

            user.table = client_config.get('table')
            user.database = client_config.get('database')
            user.server_tag = client_config.get('server_tag')

            self.fill_dynamic_user(user, user_raw)

            try:
                # some fields might not be basic types (Decimal, datetime)
                # by using IgnoreErrorJSONEncoder with JSON encode we verify that this
                # will pass a JSON encode later by mongo
                user.set_raw(json.loads(json.dumps(
                    user_raw, cls=IgnoreErrorJSONEncoder)))
            except Exception:
                logger.exception(f'Can\'t set raw for {user_raw}')

            return user
        except Exception:
            logger.exception(f'Problem with fetching User for {user_raw}')
            return None

    def _parse_users_raw_data(self, users_raw_data):
        for user_raw, client_config, sql_type in users_raw_data:
            user = self._create_user(user_raw, client_config)
            if user:
                yield user

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'devices_fetched_at_a_time',
                    'title': 'SQL pagination',
                    'type': 'integer'
                }
            ],
            'required': [
                'devices_fetched_at_a_time'
            ],
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
