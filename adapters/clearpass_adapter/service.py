import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from clearpass_adapter.connection import ClearpassConnection
from clearpass_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class ClearpassAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        endpoint_status = Field(str, 'Endpoint Status')
        endpoint_attributes = Field(str, 'Endpoint Attributes')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def _connect_client(client_config):
        try:
            with ClearpassConnection(domain=client_config['domain'],
                                     verify_ssl=client_config['verify_ssl'],
                                     username=client_config['username'],
                                     password=client_config['password'],
                                     client_id=client_config['client_id'],
                                     client_secret=client_config['client_secret'],
                                     https_proxy=client_config.get('https_proxy')) as connection:
                return connection
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
        The schema ClearpassAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Clearpass Domain',
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
                    'name': 'client_id',
                    'title': 'Client ID',
                    'type': 'string'
                },
                {
                    'name': 'client_secret',
                    'title': 'Client Secret',
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
                'client_id',
                'client_secret',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_endpoint_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            mac = device_raw.get('mac_address') or ''
            device_id = str(device_raw.get('id') or '')
            if mac or device_id:
                device.id = f'{device_id}_{mac}'
            else:
                logger.warning(f'Bad device with no id {device_raw}')
                return None
            if mac:
                device.add_nic(mac, None)
            device.description = device_raw.get('description')
            device.endpoint_status = device_raw.get('status')
            device.endpoint_attributes = device_raw.get('attributes')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Clearpass Device for {device_raw}')
            return None

    def _create_network_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            ip_address = device_raw.get('ip_address') or ''
            name = device_raw.get('name') or ''
            if name:
                device.name = name
            device_id = str(device_raw.get('id') or '')
            if name or device_id:
                device.id = f'{device_id}_{name}'
            else:
                logger.warning(f'Bad device with no id {device_raw}')
                return None
            if ip_address:
                device.add_nic(ip_address, None)
            device.description = device_raw.get('description')
            device.device_manufacturer = device_raw.get('vendor_name')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Clearpass Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, device_type in devices_raw_data:
            device = None
            if device_type == 'endpoint':
                device = self._create_endpoint_device(device_raw)
            elif device_type == 'network-device':
                device = self._create_network_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
