import logging
import ipaddress

from axonius.adapter_base import AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.files import get_local_config_file
from guardium_adapter.connection import GuardiumConnection
from guardium_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class GuardiumAdapter(ScannerAdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        # AUTOADAPTER - add here device fields if needed
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
        connection = GuardiumConnection(domain=client_config['domain'],
                                        verify_ssl=client_config['verify_ssl'],
                                        https_proxy=client_config.get('https_proxy'),
                                        username=client_config['username'],
                                        password=client_config['password'],
                                        client_id=client_config['client_id'],
                                        client_secret=client_config['client_secret'])
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
        The schema GuardiumAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Guardium Domain',
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

    def _create_stap_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('stap_id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('stap_host') or '')
            try:
                ipaddress.ip_address(device_raw.get('stap_host'))
                device.add_nic(ips=[device_raw.get('stap_host')])
            except Exception:
                device.hostname = device_raw.get('stap_host')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Guardium Device for {device_raw}')
            return None

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('CLIENT_ID')
            if device_id is None:
                if device_raw.get('stap_id'):
                    return self._create_stap_device(device_raw)
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('IP') or '')
            device.add_nic(ips=[device_raw.get('IP')])
            device.figure_os((device_raw.get('OS') or '')
                             + ' ' + (device_raw.get('OS_VENDOR') or '')
                             + ' ' + (device_raw.get('OS_VENDOR_VERSION') or ''))
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Guardium Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
