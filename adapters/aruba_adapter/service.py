import datetime
import logging

from aruba_adapter import arubaapi
from aruba_adapter.connection import ArubaConnection
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_date, format_mac

logger = logging.getLogger(f'axonius.{__name__}')


class ArubaAdapter(AdapterBase):

    #pylint: disable =R0902
    class MyDeviceAdapter(DeviceAdapter):
        device_type = Field(str, 'Device Type', enum=['Arp Device', 'Client Airwave'])
        protocol = Field(str, 'Protocol')
        vlan = Field(str, 'Vlan')
        connect_time = Field(datetime.datetime, 'Connect Time')
        duration = Field(str, 'Duration')
        wifi_vlan = Field(str, 'Wifi Vlan')
        vpn_hostname = Field(str, 'VPN Hostame')
        is_guest_user = Field(bool, 'Is Guest User')
        aruba_device_type = Field(str, 'Device Type')
        role = Field(str, 'Role')
        ssid = Field(str, 'SSID')
        wifi_phone_number = Field(str, 'Phone Number')
        wifi_notes = Field(str, 'Notes')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    @staticmethod
    def _get_client_id(client_config):
        return client_config['domain']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'), client_config.get('port'))

    @staticmethod
    def _connect_client(client_config):
        port = client_config.get('port')
        if not port:
            port = None
        try:
            if str(port) != '443':
                connection = arubaapi.ArubaAPI(device=client_config['domain'], username=client_config['username'],
                                               password=client_config['password'],
                                               insecure=not client_config.get('verify_ssl'),
                                               port=port)
                session_type = 'basic_aruba'
            else:
                connection = ArubaConnection(domain=client_config['domain'],
                                             username=client_config['username'],
                                             password=client_config['password'],
                                             verify_ssl=client_config.get('verify_ssl') or False)
                session_type = 'airwave'
            with connection:
                pass  # check that the connection credentials are valid
            return connection, session_type
        except Exception as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        session, session_type = client_data
        with session:
            if session_type == 'basic_aruba':
                for device_raw in list(client_data.cli('show arp').get('T1', []))[1:]:
                    yield device_raw, session_type
            if session_type == 'airwave':
                for device_raw in session.get_device_list():
                    yield device_raw, session_type

    # pylint: disable =R0912,R0915
    def _create_device_airwave(self, device_raw, mac_set: set):
        device = self._new_device_adapter()
        device.device_type = 'Client Airwave'
        mac = device_raw.get('mac')
        if not mac:
            logger.warning(f'Device with no mac {device_raw}')
            return None
        if mac in mac_set:
            return None
        mac_set.add(mac)
        device.id = mac
        lan_ip = device_raw.get('lan_ip')
        lan_ips = device_raw.get('lan_ips')
        ips = [lan_ip] if lan_ip else None
        if lan_ips and isinstance(lan_ips, list) and ips:
            ips.extend(lan_ips)
        if lan_ips and isinstance(lan_ips, list) and not ips:
            ips = lan_ips
        try:
            device.add_nic(mac, ips)
        except Exception:
            logger.exception(f'Problem adding nic to {device_raw}')
        try:
            try:
                connect_time = parse_date(device_raw.get('connect_time'))
            except Exception:
                logger.exception(f'If this happens call Avidor ASAP')
                connect_time = None
            if connect_time is None:
                connect_time = datetime.datetime.fromtimestamp(int(device_raw.get('connect_time')))
            if connect_time:
                device.connect_time = connect_time
        except Exception:
            logger.exception(f'Problem getting connect time for {device_raw}')
        device.duration = device_raw.get('duration')
        username = device_raw.get('username')
        try:
            if username and isinstance(username, str):
                device.last_used_users = username.split(',')
        except Exception:
            logger.exception(f'Problem adding user to {device_raw}')
        device.wifi_vlan = device_raw.get('vlan')
        try:
            device.figure_os((device_raw.get('device_os') or '') + ' ' + (device_raw.get('device_os_detail') or ''))
        except Exception:
            logger.exception(f'Problem getting os for {device_raw}')
        try:
            lan_hostname = device_raw.get('lan_hostname')
            lan_hostnames = device_raw.get('lan_hostnames')
            if lan_hostname:
                device.hostname = lan_hostname
            elif lan_hostnames:
                device.hostname = lan_hostnames[0]
        except Exception:
            logger.exception(f'Problem getting hostnames for {device_raw}')
        device.vpn_hostname = device_raw.get('vpn_hostname')
        is_guest_user = device_raw.get('is_guest_user')
        if is_guest_user in ['YES', '1']:
            device.is_guest_user = True
        elif is_guest_user in ['NO', '0']:
            device.is_guest_user = False
        device.aruba_device_type = device_raw.get('device_type')
        device.role = device_raw.get('role')
        device.ssid = device_raw.get('ssid')
        device.wifi_phone_number = device_raw.get('phone_number')
        device.wifi_notes = device_raw.get('notes')

        device.set_raw(device_raw)
        return device

    def _create_device_basic_aruba(self, device_raw):
        device = self._new_device_adapter()
        device.device_type = 'Arp Device'
        # We assume that device_data_list starts with Protocol, IP Address and MacAddres and then VLAN
        # If no VLAN is attached we will put ''
        device_data_list = [data_from_xml.strip() for data_from_xml in device_raw.split('\t')]
        device_data_list = list(filter(lambda x: x != '', device_data_list))
        if len(device_data_list) < 3:
            logger.error(f'Bad device data list {str(device_data_list)}')
            return None
        if len(device_data_list) == 3:
            logger.warning(f'No interface name for {str(device_data_list)}')
            device_data_list.append('')
        mac = format_mac(device_data_list[2])
        if not mac:
            logger.error(f'No mac address! for {device_raw}')
            return None
        device.id = mac
        try:
            device.add_nic(mac=mac)
        except Exception:
            logger.exception(f'Problem adding nic to {str(device_data_list)}')
        try:
            device.set_related_ips(ips=[device_data_list[1]])
        except Exception:
            logger.exception(f'Problem adding linked device to {str(device_data_list)}')
        device.protocol = str(device_data_list[0])
        device.vlan = str(device_data_list[3])
        device.set_raw({'data': device_data_list})
        return device

    def _parse_raw_data(self, devices_raw_data):
        mac_set = set()
        for device_raw, session_type in devices_raw_data:
            try:
                if session_type == 'basic_aruba':
                    device = self._create_device_basic_aruba(device_raw)
                    if device:
                        yield device
                if session_type == 'airwave':
                    device = self._create_device_airwave(device_raw, mac_set)
                    if device:
                        yield device
            except Exception:
                logger.exception(f'Problem with fetching Aruba Device {str(device_raw)}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]

    @staticmethod
    def _clients_schema():
        """
        The schema ArubaAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Aruba Host',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'Port',
                    'type': 'integer',
                    'format': 'port'
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

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        """
        To be implemented by inheritors, otherwise leave empty.
        :type correlation_cmd_result: str
        :param correlation_cmd_result: result of running cmd on a machine
        :type os_type: str
        :param os_type: the type of machine ran upon
        :return:
        """
        raise NotImplementedError()
