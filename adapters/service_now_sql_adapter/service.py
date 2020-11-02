import logging
from functools import partial

from axonius.clients.service_now.external import service_now_sql_get_connection
from axonius.clients.service_now.service.base import ServiceNowAdapterBase
from axonius.clients.service_now.service.structures import SnowDeviceAdapter, SnowUserAdapter
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.adapter_base import AdapterProperty
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.service_now.service import sql_consts as consts
from service_now_sql_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class ServiceNowSqlAdapter(ServiceNowAdapterBase, Configurable):

    ###
    # Note: Most of the logic occurs in ServiceNowAdapterBase
    ###

    class MyDeviceAdapter(SnowDeviceAdapter):
        pass

    class MyUserAdapter(SnowUserAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('server'),
                                                port=client_config.get('port'))

    def get_connection_external(self):
        return partial(service_now_sql_get_connection,
                       devices_fetched_at_a_time=self._devices_fetched_at_a_time)

    def get_connection(self, client_config):
        connection = self.get_connection_external()(client_config)
        return connection

    def _clients_schema(self):
        """
        The schema ServiceNowSqlAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': consts.SERVICE_NOW_SQL_HOST,
                    'title': 'ServiceNow SQL Server',
                    'type': 'string'
                },
                {
                    'name': consts.SERVICE_NOW_SQL_PORT,
                    'title': 'Port',
                    'type': 'integer',
                    'default': consts.DEFAULT_SERVICE_NOW_SQL_PORT,
                    'format': 'port'
                },
                {
                    'name': consts.SERVICE_NOW_SQL_DATABASE,
                    'title': 'Database',
                    'type': 'string',
                    'default': consts.DEFAULT_SERVICE_NOW_SQL_DATABASE
                },
                {
                    'name': consts.USER,
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': consts.PASSWORD,
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                *ServiceNowAdapterBase.SERVICE_NOW_CLIENTS_SCHEMA_ITEMS,
            ],
            'required': [
                consts.SERVICE_NOW_SQL_HOST,
                consts.USER,
                consts.PASSWORD,
                consts.SERVICE_NOW_SQL_DATABASE,
                *ServiceNowAdapterBase.SERVICE_NOW_CLIENTS_SCHEMA_REQUIRED,
            ],
            'type': 'array'
        }

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.UserManagement]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                *ServiceNowAdapterBase.SERVICE_NOW_DB_CONFIG_SCHEMA_ITEMS,
                {
                    'name': 'devices_fetched_at_a_time',
                    'type': 'integer',
                    'title': 'SQL pagination'
                }
            ],
            'required': [
                *ServiceNowAdapterBase.SERVICE_NOW_DB_CONFIG_SCHEMA_REQUIRED,
                'devices_fetched_at_a_time'
            ],
            'pretty_name': 'ServiceNow Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            **ServiceNowAdapterBase.SERVICE_NOW_DB_CONFIG_DEFAULT,
            'devices_fetched_at_a_time': 1000
        }

    def _on_config_update(self, config):
        devices_fetched_at_a_time = (config.get('devices_fetched_at_a_time') or
                                     consts.DEFAULT_DEVICES_FETECHED_AT_A_TIME)
        # inject parallel_requests
        config['parallel_requests'] = devices_fetched_at_a_time
        super()._on_config_update(config)
        self._devices_fetched_at_a_time = devices_fetched_at_a_time
