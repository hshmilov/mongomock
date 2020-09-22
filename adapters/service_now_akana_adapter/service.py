import logging

from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.service_now import consts
from axonius.clients.service_now.akana import ServiceNowAkanaConnection
from axonius.clients.service_now.service.adapter_base import ServiceNowAdapterBase
from axonius.clients.service_now.service.structures import SnowDeviceAdapter, SnowUserAdapter
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from service_now_akana_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class ServiceNowAkanaAdapter(ServiceNowAdapterBase, Configurable):

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
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        try:
            connection = ServiceNowAkanaConnection(domain=client_config.get('domain'),
                                                   token_endpoint=client_config.get('token_endpoint'),
                                                   verify_ssl=client_config.get('verify_ssl'),
                                                   https_proxy=client_config.get('https_proxy'),
                                                   proxy_username=client_config.get('proxy_username'),
                                                   proxy_password=client_config.get('proxy_password'),
                                                   username=client_config.get('username'),
                                                   password=client_config.get('password'))
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.warning(message, exc_info=True)
            raise ClientConnectionException(message)

    @staticmethod
    def _clients_schema():
        """
        The schema ServiceNowAkanaAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Akana API Domain',
                    'type': 'string'
                },
                {
                    'name': 'token_endpoint',
                    'title': 'Auth Token Endpoint',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'Akana App ID',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Akana Secret',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
                {
                    'name': 'proxy_username',
                    'title': 'HTTPS Proxy User Name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS Proxy Password',
                    'type': 'string',
                    'format': 'password'
                },
                *ServiceNowAdapterBase.SERVICE_NOW_CLIENTS_SCHEMA_ITEMS
            ],
            'required': [
                'domain',
                'token_endpoint',
                'username',
                'password',
                'verify_ssl',
                *ServiceNowAdapterBase.SERVICE_NOW_CLIENTS_SCHEMA_REQUIRED
            ],
            'type': 'array'
        }

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                *ServiceNowAdapterBase.SERVICE_NOW_DB_CONFIG_SCHEMA_ITEMS,
                {
                    'name': 'async_chunks',
                    'type': 'integer',
                    'title': 'Number of requests to perform in parallel'
                },
            ],
            'required': [
                *ServiceNowAdapterBase.SERVICE_NOW_DB_CONFIG_SCHEMA_REQUIRED,
                'async_chunks',
            ],
            'pretty_name': 'ServiceNow Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            **ServiceNowAdapterBase.SERVICE_NOW_DB_CONFIG_DEFAULT,
            'async_chunks': consts.DEFAULT_ASYNC_CHUNK_SIZE
        }

    def _on_config_update(self, config):
        # inject parallel_requests
        config['parallel_requests'] = config.get('async_chunks') or consts.DEFAULT_ASYNC_CHUNK_SIZE
        super()._on_config_update(config)
