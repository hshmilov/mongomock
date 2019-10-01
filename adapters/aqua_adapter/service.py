import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import ListField, Field
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from aqua_adapter.connection import AquaConnection
from aqua_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class AquaAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        server_name = Field(str, 'Server Name')
        allowed_labels = ListField(str, 'Allowed Labels')
        allowed_registries = ListField(str, 'Allowed Registries')
        total_pass = Field(int, 'Total Pass')
        total_warn = Field(str, 'Total Warnings')
        gateways = ListField(str, 'Gateways')
        is_scan = Field(bool, 'Is Scan')

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
        connection = AquaConnection(domain=client_config['domain'],
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
        The schema AquaAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Aqua Domain',
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
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('logicalname') or '')
            device.name = device_raw.get('logicalname')
            device.last_seen = parse_date(device_raw.get('lastupdate'))
            device.hostname = device_raw.get('hostname')
            device.total_warn = device_raw.get('total_warn') if isinstance(device_raw.get('total_warn'), int) else None
            device.total_pass = device_raw.get('total_pass') if isinstance(device_raw.get('total_pass'), int) else None
            device.figure_os(device_raw.get('host_os'))
            device.server_name = device_raw.get('server_name')
            if isinstance(device_raw.get('allowed_labels'), list):
                device.allowed_labels = device_raw.get('allowed_labels')
            if isinstance(device_raw.get('allowed_registries'), list):
                device.allowed_registries = device_raw.get('allowed_registries')
            if isinstance(device_raw.get('gateways'), list):
                device.gateways = device_raw.get('gateways')
            device.is_scan = device_raw.get('scan')
            if device_raw.get('address') and isinstance(device_raw.get('address'), str):
                device.add_nic(ips=device_raw.get('address').split(','))
            if device_raw.get('public_address') and isinstance(device_raw.get('public_address'), str):
                device.add_nic(ips=device_raw.get('public_address').split(','))
                device.add_public_ip(ip=device_raw.get('public_address'))
            device.add_agent_version(agent=AGENT_NAMES.aqua, version=device_raw.get('version'),
                                     status=device_raw.get('status'))
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Aqua Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
