import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from packetfence_adapter.connection import PacketfenceConnection
from packetfence_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class PacketfenceAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        autoreg = Field(str, 'Autoreg')
        notes = Field(str, 'Notes')
        last_dhcp = Field(datetime.datetime, 'Last DHCP')
        last_arp = Field(datetime.datetime, 'Last ARP')
        lastskip = Field(datetime.datetime, 'Last Skip')
        machine_account = Field(str, 'Machine Account')
        detect_date = Field(datetime.datetime, 'Detect Time')
        bypass_vlan = Field(str, 'Bypass VLAN')
        voip = Field(str, 'VOIP')
        unregdate = Field(str, 'Unregdate')
        user_agent = Field(str, 'User Agent')
        pid = Field(str, 'PID')
        device_status = Field(str, 'Device Status')
        device_score = Field(int, 'Device Score')
        device_class = Field(str, 'Device Class')

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
        connection = PacketfenceConnection(domain=client_config['domain'],
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
        The schema PacketfenceAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Packetfence Domain',
                    'type': 'string'
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
                    'type': 'string'
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
            if not (device_raw.get('mac') or device_raw.get('computername')):
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = (device_raw.get('mac') or '') + '_' + (device_raw.get('computername') or '')
            device.hostname = device_raw.get('computername')
            device.add_nic(mac=device_raw.get('mac'))
            device.autoreg = device_raw.get('autoreg')
            device.device_manufacturer = device_raw.get('device_manufacturer')
            device.notes = device_raw.get('notes')
            device.last_seen = parse_date(device_raw.get('last_seen'))
            device.lastskip = parse_date(device_raw.get('lastskip'))
            device.last_dhcp = parse_date(device_raw.get('last_dhcp'))
            device.last_arp = parse_date(device_raw.get('last_arp'))
            device.machine_account = device_raw.get('machine_account')
            device.detect_date = parse_date(device_raw.get('detect_date'))
            device.bypass_vlan = device_raw.get('bypass_vlan')
            device.user_agent = device_raw.get('user_agent')
            device.voip = device_raw.get('voip')
            device.pid = device_raw.get('pid')
            device.device_class = device_raw.get('device_class')
            device.device_score = device_raw.get('device_score')\
                if isinstance(device_raw.get('device_score'), int) else None
            device.device_status = device_raw.get('status')
            device.unregdate = device_raw.get('unregdate')

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Packetfence Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
