import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.datetime import parse_date
from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from bigfix_inventory_adapter.connection import BigfixInventoryConnection
from bigfix_inventory_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class BigfixInventoryAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        is_deleted = Field(bool, 'Is Deleted')
        deletion_date = Field(datetime.datetime, 'Deletion Time')
        computer_group_id = Field(int, 'Computer Group Id')

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
        connection = BigfixInventoryConnection(domain=client_config['domain'],
                                               verify_ssl=client_config['verify_ssl'],
                                               https_proxy=client_config.get('https_proxy'),
                                               username=client_config.get('username'),
                                               password=client_config.get('password'),
                                               apikey=client_config.get('apikey'))
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
        The schema BigfixInventoryAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'BigFix Inventory Domain',
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
                    'name': 'apikey',
                    'title': 'API Token (For MFA Cases)',
                    'type': 'string'
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
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw, sw_dict):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            try:
                sw_data = sw_dict.get(device_id)
                if not isinstance(sw_data, list):
                    sw_data = []
                for sw_raw in sw_data:
                    device.add_installed_software(name=sw_raw.get('product_name'),
                                                  version=sw_raw.get('product_release'),
                                                  vendor=sw_raw.get('product_publisher_name'))
            except Exception:
                logger.exception(f'Problem getting sw for {device_raw}')
            device.name = device_raw.get('name')
            device.hostname = device_raw.get('dns_name')
            device.computer_group_id = device_raw.get('computer_group_id')\
                if isinstance(device_raw.get('computer_group_id'), int) else None
            device.figure_os((device_raw.get('os') or '') + ' ' + (device_raw.get('os_type') or ''))
            device.last_seen = parse_date(device_raw.get('last_seen'))
            device.first_seen = parse_date(device_raw.get('first_seen'))
            device.deletion_date = parse_date(device_raw.get('deletion_date'))

            if isinstance(device_raw.get('is_deleted'), int):
                device.is_deleted = device_raw.get('is_deleted') == 1
            elif isinstance(device_raw.get('is_deleted'), bool):
                device.is_deleted = device_raw.get('is_deleted')
            if isinstance(device_raw.get('ip_address'), list):
                device.add_nic(ips=device_raw.get('ip_address'))
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching BigfixInventory Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, sw_dict in devices_raw_data:
            device = self._create_device(device_raw, sw_dict)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
