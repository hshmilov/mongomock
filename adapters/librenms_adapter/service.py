import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from librenms_adapter.connection import LibrenmsConnection
from librenms_adapter.client_id import get_client_id
from librenms_adapter.consts import DEFAULT_DOMAIN

logger = logging.getLogger(f'axonius.{__name__}')


class LibrenmsAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        icon = Field(str, 'Icon')
        location = Field(str, 'Location')

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
        connection = LibrenmsConnection(domain=client_config['domain'],
                                        verify_ssl=client_config['verify_ssl'],
                                        https_proxy=client_config.get('https_proxy'),
                                        apikey=client_config['apikey'])
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
        The schema LibrenmsAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Librenms Domain',
                    'type': 'string',
                    'default': DEFAULT_DOMAIN
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
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
                    'type': 'bool'
                }
            ],
            'required': [
                'domain',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('device_id') or 'hostname')
            device.hostname = device_raw.get('hostname')
            device.device_serial = device_raw.get('serial')
            device.figure_os(device_raw.get('os'))
            device.icon = device_raw.get('icon')
            device.location = device_raw.get('location')
            mac = device_raw.get('mac')
            if not mac:
                mac = None
            ips = []
            if device_raw.get('ipv4') and isinstance(device_raw.get('ipv4'), str):
                ips.extend(device_raw.get('ipv4').split(','))
            if device_raw.get('ipv6') and isinstance(device_raw.get('ipv6'), str):
                ips.extend(device_raw.get('ipv6').split(','))
            if not ips:
                ips = None
            if mac or ips:
                device.add_nic(mac=mac, ips=ips)
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Librenms Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
