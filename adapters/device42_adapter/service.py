import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.datetime import parse_date
from axonius.fields import Field, ListField
from axonius.utils.files import get_local_config_file
from device42_adapter.connection import Device42Connection
from device42_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class Device42Adapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        customer = Field(str, 'Customer')
        building = Field(str, 'Building')
        category = Field(str, 'Category')
        aliases = ListField(str, 'Aliases')
        groups = ListField(str, 'Groups')
        last_updated = Field(datetime.datetime, 'Last Updated')
        in_service = Field(bool, 'In Service')
        notes = Field(str, 'Notes')
        device_type = Field(str, 'Device Type')
        device_tags = ListField(str, 'Device Tags')
        room = Field(str, 'Room')

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
        connection = Device42Connection(domain=client_config['domain'],
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
        The schema Device42Adapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Device42 Domain',
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

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('device_id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            device.hostname = device_raw.get('name')
            device.customer = device_raw.get('customer')
            device.building = device_raw.get('building')
            device.category = device_raw.get('category')
            try:
                if device_raw.get('aliases') and isinstance(device_raw.get('aliases'), list):
                    device.aliases = device_raw.get('aliases')
            except Exception:
                logger.exception(f'Problem getting alliases for {device_raw}')
            try:
                if device_raw.get('groups') and isinstance(device_raw.get('groups'), str):
                    device.groups = device_raw.get('groups').split(',')
            except Exception:
                logger.exception(f'Problem getting groups for {device_raw}')
            try:
                device.last_updated = parse_date(device_raw.get('last_updated'))
            except Exception:
                logger.exception(f'Problem gettins last updated {device_raw}')
            if isinstance(device_raw.get('in_service'), bool):
                device.in_service = device_raw.get('in_service')
            try:
                if device_raw.get('ip_addresses') and isinstance(device_raw.get('ip_addresses'), list):
                    for nic in device_raw.get('ip_addresses'):
                        try:
                            ip = nic.get('ip')
                            if not ip:
                                ip = None
                            else:
                                ip = ip.split(',')
                            mac = nic.get('macaddress')
                            if not mac:
                                mac = None
                            if ip or mac:
                                device.add_nic(mac, ip, name=nic.get('subnet'))
                        except Exception:
                            logger.exception(f'Problem getting nic {nic}')
            except Exception:
                logger.exception(f'Problem adding nic to {device_raw}')
            device.device_manufacturer = device_raw.get('manufacturer')
            device.notes = device_raw.get('notes')
            try:
                device.figure_os((device_raw.get('os') or '') + ' ' + str(device_raw.get('osarch') or ''))
            except Exception:
                logger.exception(f'Problem getting os for {device_raw}')
            device.device_serial = device_raw.get('serial_no')
            device.device_type = device_raw.get('type')
            device.uuid = device_raw.get('uuid') if device_raw.get('uuid') else None
            try:
                if isinstance(device_raw.get('tags'), list):
                    device.device_tags = device_raw.get('tags')
            except Exception:
                logger.exception(f'Problem getting tags for {device_raw}')
            device.room = device_raw.get('room')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Device42 Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
