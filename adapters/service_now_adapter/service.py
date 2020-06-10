import logging

from axonius.adapter_base import AdapterProperty
from axonius.clients.service_now import consts
from axonius.clients.service_now.service.adapter_base import ServiceNowAdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.service_now.connection import ServiceNowConnection
from axonius.clients.service_now.service.structures import SnowDeviceAdapter, SnowUserAdapter
from axonius.mixins.configurable import Configurable
from axonius.types.correlation import CorrelationResult, CorrelationReason
from axonius.plugin_base import add_rule, return_error, EntityType
from axonius.utils.files import get_local_config_file
logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=line-too-long


class ServiceNowAdapter(ServiceNowAdapterBase, Configurable):

    ###
    # Note: Most of the logic occurres in ServiceNowAdapterBase
    ###

    class MyDeviceAdapter(SnowDeviceAdapter):
        pass

    class MyUserAdapter(SnowUserAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        try:
            https_proxy = client_config.get('https_proxy')
            if https_proxy and https_proxy.startswith('http://'):
                https_proxy = 'https://' + https_proxy[len('http://'):]
            connection = ServiceNowConnection(
                domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                username=client_config['username'],
                password=client_config['password'], https_proxy=https_proxy)
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.warning(message, exc_info=True)
            raise ClientConnectionException(message)

    def _clients_schema(self):
        """
        The schema ServiceNowAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'ServiceNow Domain',
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
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
                *ServiceNowAdapterBase.SERVICE_NOW_CLIENTS_SCHEMA_ITEMS,
            ],
            'required': [
                'domain',
                'username',
                'password',
                'verify_ssl',
                *ServiceNowAdapterBase.SERVICE_NOW_CLIENTS_SCHEMA_REQUIRED
            ],
            'type': 'array'
        }

    @add_rule('update_computer', methods=['POST'])
    def update_service_now_computer(self):
        if self.get_method() != 'POST':
            return return_error('Method not supported', 405)
        service_now_connection = self.get_request_data_as_object()
        success = False
        for client_id in self._clients:
            try:
                conn = self.get_connection(self._get_client_config_by_client_id(client_id))
                with conn:
                    result_status, device_raw = conn.update_service_now_computer(service_now_connection)
                    success = success or result_status
                    if success is True:
                        device = self.create_snow_device(device_raw=device_raw,
                                                         fetch_ips=self.__fetch_ips)
                        if device:
                            device_dict = device.to_dict()
                            self._save_data_from_plugin(
                                client_id,
                                {'raw': [], 'parsed': [device_dict]},
                                EntityType.Devices, False)
                            self._save_field_names_to_db(EntityType.Devices)
                        return '', 200
            except Exception:
                logger.exception(f'Could not connect to {client_id}')
        return 'Failure', 400

    @add_rule('create_incident', methods=['POST'])
    def create_service_now_incident(self):
        if self.get_method() != 'POST':
            return return_error('Medhod not supported', 405)
        service_now_dict = self.get_request_data_as_object()
        success = False
        for client_id in self._clients:
            try:
                conn = self.get_connection(self._get_client_config_by_client_id(client_id))
                with conn:
                    success = success or conn.create_service_now_incident(service_now_dict)
                    if success is True:
                        return '', 200
            except Exception:
                logger.exception(f'Could not connect to {client_id}')
        return 'Failure', 400

    @add_rule('create_computer', methods=['POST'])
    def create_service_now_computer(self):
        if self.get_method() != 'POST':
            return return_error('Method not supported', 405)
        request_json = self.get_request_data_as_object()
        service_now_dict = request_json.get('snow')
        success = False
        for client_id in self._clients:
            try:
                conn = self.get_connection(self._get_client_config_by_client_id(client_id))
                with conn:
                    result_status, device_raw = conn.create_service_now_computer(service_now_dict)
                    success = success or result_status
                    if success is True:
                        device = self.create_snow_device(device_raw=device_raw,
                                                         fetch_ips=self.__fetch_ips)
                        if device:
                            device_id = device.id
                            device_dict = device.to_dict()
                            self._save_data_from_plugin(
                                client_id,
                                {'raw': [], 'parsed': [device_dict]},
                                EntityType.Devices, False)
                            self._save_field_names_to_db(EntityType.Devices)
                            to_correlate = request_json.get('to_ccorrelate')
                            if isinstance(to_correlate, dict):
                                to_correlate_plugin_unique_name = to_correlate.get('to_correlate_plugin_unique_name')
                                to_correlate_device_id = to_correlate.get('device_id')
                                if to_correlate_plugin_unique_name and to_correlate_device_id:
                                    correlation_param = CorrelationResult(associated_adapters=[(to_correlate_plugin_unique_name,
                                                                                                to_correlate_device_id),
                                                                                               (self.plugin_unique_name, device_id)],
                                                                          data={'reason': 'ServiceNow Device Creation'},
                                                                          reason=CorrelationReason.ServiceNowCreation)
                                    self.link_adapters(EntityType.Devices, correlation_param)
                        return '', 200
            except Exception:
                logger.exception(f'Could not connect to {client_id}')
        return 'Failure', 400

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    def outside_reason_to_live(self) -> bool:
        """
        This adapter might be called from outside, let it live
        """
        return True

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
        super()._on_config_update(config)
        self.__parallel_requests = config.get('async_chunks') or consts.DEFAULT_ASYNC_CHUNK_SIZE
