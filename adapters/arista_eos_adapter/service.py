import logging

from axonius.utils import datetime

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter, DeviceAdapterOS
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from arista_eos_adapter.connection import AristaEosConnection
from arista_eos_adapter.client_id import get_client_id
from arista_eos_adapter.consts import BASIC_INFO, ARP_INFO, FetchProto


logger = logging.getLogger(f'axonius.{__name__}')


class AristaEosAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        arista_version = Field(str, 'EOS Version')
        arista_arch = Field(str, 'Architecture')
        fetch_proto = Field(str, 'Fetch Protocol', enum=FetchProto)
        hardware_type = Field(str, 'Hardware Type')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def get_connection(client_config):
        connection = AristaEosConnection(enable=client_config.get('enable'),
                                         domain=client_config['domain'],
                                         verify_ssl=client_config['verify_ssl'],
                                         https_proxy=client_config.get('https_proxy'),
                                         username=client_config['username'],
                                         password=client_config['password'])
        with connection:
            pass
        return connection

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
        The schema AristaEosAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Arista EOS Domain',
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
                    'name': 'enable',
                    'title': 'EOS Enable Password',
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

    def _create_arp_info(self, device_raw):

        device = self._new_device_adapter()
        device_id = device_raw.get('hwAddress')
        if device_id is None:
            logger.warning(f'Bad device with no ID {device_raw}')
            return None

        device.id = device_id + '_' + (device_raw.get('address') or '')
        device.set_raw(device_raw)
        device.add_nic(mac=device_raw.get('hwAddress'),
                       ips=[device_raw.get('address')],
                       name=device_raw.get('interface'))

        device.fetch_proto = FetchProto.ARP.name

        return device

    @classmethod
    def _map_interface_address(cls, interface: list, ip_list: list, subnet_list: list):
        interfacaddress = interface['interfaceAddress'][0]
        # Primary Address
        if interfacaddress['primaryIp']:
            primary_ip = interfacaddress['primaryIp']['address']
            mask = interfacaddress['primaryIp']['maskLen']
            ip_list.append(primary_ip)
            subnet_list.append(primary_ip + '/' + str(mask))
            # Secondary List Address
            if interfacaddress['secondaryIps'] and isinstance(interfacaddress['secondaryIps'], dict):
                for secondary_ip in interfacaddress['secondaryIps']:
                    ip = interfacaddress['secondaryIps'][secondary_ip]['address']
                    mask = interfacaddress['secondaryIps'][secondary_ip]['maskLen']
                    ip_list.append(ip)
                    subnet_list.append(ip + '/' + str(mask))

    @staticmethod
    def _get_interface_admin_status(admin_status=None):
        if admin_status == 'connected':
            return 'Up'
        if admin_status == 'notconnect':
            return 'Down'
        return None

    @classmethod
    def _get_network_device_interfaces(cls, device: DeviceAdapter, interface_raw: dict):

        for interface_name, interface in interface_raw.items():

            ip_list = []
            subnet_list = []
            vlans_data = []

            try:
                if 'interfaceAddress' in interface and interface['interfaceAddress']:
                    cls._map_interface_address(interface, ip_list, subnet_list)

                device.add_nic(
                    mac=interface.get('physicalAddress'),
                    name=interface.get('name'),
                    operational_status=interface.get('lineProtocolStatus'),
                    admin_status=cls._get_interface_admin_status(interface.get('interfaceStatus')),
                    speed=interface.get('bandwidth'),
                    mtu=interface.get('mtu'),
                    ips=ip_list,
                    subnets=subnet_list,
                    vlans=vlans_data
                )

            except Exception:
                logger.exception('Exception during interfaces handling !  ')

    def _create_basic_info(self, device_raw):

        device = self._new_device_adapter()

        device_id = device_raw.get('systemMacAddress')
        if device_id is None:
            logger.warning(f'Bad device with no ID {device_raw}')
            return None
        device.id = device_id + '_' + (device_raw.get('serialNumber') or '')

        device.add_nic(mac=device_raw.get('systemMacAddress'))

        device.device_model = device_raw.get('modelName')
        device.device_serial = device_raw.get('serialNumber')

        device.arista_version = device_raw.get('version')
        device.arista_arch = device_raw.get('architecture')

        device.os = DeviceAdapterOS()
        device.os.type = 'Arista'
        device.os.build = device_raw.get('internalBuildId')
        try:
            uptime = datetime.timedelta(microseconds=float(device_raw.get('bootupTimestamp')))
            device.set_boot_time(uptime=uptime)
        except ValueError:
            logger.exception('Failed to parse device boot time stamp ')

        try:
            if device_raw.get('memTotal'):
                device.total_physical_memory = float(device_raw.get('memTotal')) / 1024 / 1024
            if device_raw.get('memFree'):
                device.free_physical_memory = float(device_raw.get('memFree')) / 1024 / 1024

            hostname = device_raw.get('hostname') or None
            fqdn = device_raw.get('fqdn') or None
            device.hostname = hostname
            if hostname and fqdn and hostname in fqdn:
                device.domain = fqdn.strip(hostname)[1:]

        except Exception:
            logger.exception('Exception during network device basic info ')

        if device_raw.get('interfaces') and isinstance(device_raw.get('interfaces'), dict):
            self._get_network_device_interfaces(device, device_raw.get('interfaces'))

        device.fetch_proto = FetchProto.BASIC_INFO.name
        device.adapter_properties = [AdapterProperty.Network, AdapterProperty.Manager]
        return device

    def _create_device(self, device_raw):
        try:

            if device_raw.get(BASIC_INFO):
                return self._create_basic_info(device_raw.get(BASIC_INFO))
            if device_raw.get(ARP_INFO):
                return self._create_arp_info(device_raw.get(ARP_INFO))

            logger.error(f'got unknown data , do not know what to do with that {device_raw}')
            return None

        except Exception:
            logger.exception(f'Problem with fetching Arista  Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
