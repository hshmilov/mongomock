import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.mixins.configurable import Configurable
from axonius.utils.dynamic_device_mixin import DynamicDeviceMixin
from axonius.utils.files import get_local_config_file
from sumo_logic_adapter import consts
from sumo_logic_adapter.connection import SumoLogicConnection
from sumo_logic_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class SumoLogicAdapter(AdapterBase, Configurable, DynamicDeviceMixin):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        # all fields are either dynamic or aggregated ones
        pass

    DYNAMIC_FIELD_COLLISION_TITLE_PREFIX = 'SumoLogic'

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
        connection = SumoLogicConnection(domain=client_config['domain'],
                                         access_id=client_config['access_id'],
                                         access_key=client_config['access_key'],
                                         search_query=client_config['search_query'],
                                         verify_ssl=client_config['verify_ssl'],
                                         https_proxy=client_config.get('https_proxy'))
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list(max_log_history=self.__max_log_history,
                                                   maximum_records=self.__maximum_records,
                                                   include_messages=self.__include_messages)

    @staticmethod
    def _clients_schema():
        """
        The schema SumoLogicAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Sumo Logic Service URL',
                    'type': 'string',
                    'default': consts.DEFAULT_DOMAIN,
                },
                {
                    'name': 'access_id',
                    'title': 'Access ID',
                    'type': 'string'
                },
                {
                    'name': 'access_key',
                    'title': 'Access Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'search_query',
                    'title': 'Search Query',
                    'type': 'string',
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
                }
            ],
            'required': [
                'domain',
                'access_id',
                'access_key',
                'search_query',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            self.fill_dynamic_device(device, device_raw)
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching SumoLogic Device for {device_raw}')
            return None

    # pylint: disable=arguments-differ
    def _parse_id(self, *, device_raw, gen_values, **kwargs):
        return (super()._parse_id(device_raw=device_raw, gen_values=gen_values, **kwargs)
                or device_raw.get(consts.SEARCH_RESULT_INTERNAL_FIELDS_ID))

    def _fill_dynamic_fields(self, device: DeviceAdapter, *, device_raw, **_):
        super()._fill_dynamic_fields(device, device_raw={k: v for k, v in device_raw.items()
                                                         if (not k.startswith('_') or
                                                             # only parse whitelisted internal sumo fields
                                                             k in consts.SEARCH_RESULT_INTERNAL_FIELDS_WHITELIST)})

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    def _on_config_update(self, config):
        logger.info(f'Loading Sumo Logic config: {config}')
        self.__max_log_history = int(config['max_log_history'])
        self.__maximum_records = int(config['maximum_records'])
        self.__include_messages = bool(config['include_messages'])

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'max_log_history',
                    'title': 'Number of days to fetch',
                    'type': 'number'
                },
                {
                    'name': 'maximum_records',
                    'title': 'Maximum amount of messages for search',
                    'type': 'number'
                },
                {
                    'name': 'include_messages',
                    'title': 'Consume raw messages',
                    'type': 'bool',
                },
            ],
            'required': [
                'max_log_history',
                'maximum_records',
                'include_messages',
            ],
            'pretty_name': 'Sumo Logic Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'max_log_history': 30,
            'maximum_records': 100000,
            'include_messages': False,
        }

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
