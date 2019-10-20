import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.fields import Field
from axonius.utils.parsing import parse_date
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from medigate_adapter.connection import MedigateConnection
from medigate_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class MedigateAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        vlan = Field(int, 'Vlan')
        connection_type = Field(str, 'Connection Type')
        ip_assignment = Field(str, 'Ip Assignment')
        sw_version = Field(str, 'SW Version')
        is_online = Field(bool, 'Is Online')
        category = Field(str, 'Category')
        function = Field(str, 'Function')
        device_class = Field(str, 'Class')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        connection = MedigateConnection(domain=client_config['domain'],
                                        verify_ssl=client_config['verify_ssl'],
                                        https_proxy=client_config.get('https_proxy'),
                                        username=client_config['username'],
                                        password=client_config['password'])
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

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema MedigateAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Medigate Domain',
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
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('uid')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('mac') or '')
            mac = device_raw.get('mac')
            if not mac:
                mac = None
            ip = device_raw.get('ip')
            if ip:
                ips = [ip]
            else:
                ips = None
            if mac or ips:
                device.add_nic(mac=mac, ips=ips)
            device.vlan = device_raw.get('vlan') if isinstance(device_raw.get('vlan'), int) else None
            device.first_seen = parse_date(device_raw.get('first_seen'))
            device.last_seen = parse_date(device_raw.get('last_seen'))
            device.connection_type = device_raw.get('connection_type')
            device.ip_assignment = device_raw.get('ip_assignment')
            device.device_manufacturer = device_raw.get('manufacturer')
            device.device_model = device_raw.get('model')
            device.sw_version = device_raw.get('sw_version')
            device.is_online = device_raw.get('is_online')
            device.category = device_raw.get('category')
            device.device_model_family = device_raw.get('family')
            device.function = device_raw.get('function')
            device.device_class = device_raw.get('class')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Medigate Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Network]
