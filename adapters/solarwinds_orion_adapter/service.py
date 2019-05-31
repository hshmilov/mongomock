import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.mixins.configurable import Configurable
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from solarwinds_orion_adapter.connection import SolarwindsConnection

logger = logging.getLogger(f'axonius.{__name__}')

SOLARWINDS_PORT = 17778

# pylint: disable=too-many-instance-attributes,too-many-branches,too-many-statements


class SolarwindsOrionAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        uri = Field(str, 'URI')
        ip_address_guid = Field(str, 'IP Address GUID')
        software_hardware_makeup = Field(str, 'Node Makeup')
        location = Field(str, 'Location')
        node_id = Field(str, 'NodeID')
        ssid = Field(str, 'SSID')
        first_update = Field(datetime.datetime, 'First Update')
        last_update = Field(datetime.datetime, 'Last Update')
        instance_type = Field(str, 'Instance Type')
        wifi_name = Field(str, 'Wifi Name')
        wifi_display_name = Field(str, 'Wifi Display Name')
        lan_name = Field(str, 'Lan Name')
        lan_display_name = Field(str, 'Lan Display Name')
        connected_to = Field(str, 'Connected To')
        connection_type_name = Field(str, 'Connection Type Name')
        port_number = Field(str, 'Port Number')
        port_name = Field(str, 'Port Name')
        solar_vlan = Field(str, 'Solarwinds VLAN')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        """
        :param client_config: client configuration includes password, username and domain
        :return: the domain, or patrolling ip address
        """
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'), SOLARWINDS_PORT)

    def _connect_client(self, client_config):
        """
        Creates a solarwinds connection by creating an instance of Solarwinds Connection
        :param client_config: client configuration includes password, username and domain
        :return: instance of Solarwinds connection
        """

        try:
            connection = SolarwindsConnection(domain=client_config['domain'],
                                              username=client_config['username'],
                                              password=client_config['password'],
                                              verify_ssl=client_config['verify_ssl'])

            connection.connect()
            return connection
        except Exception as e:
            logger.error('Failed to connect to client %s', self._get_client_id(client_config))
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get a list of all of the devices used by the client
        :param client_name:
        :param session: instance of SolarWinds connection
        :return: device list of the patrolling user's devices
        """
        client_data.connect()
        yield from client_data.get_device_list(fetch_ipam=self.__fetch_ipam)

    def _clients_schema(self):
        """
        Denotes the clients schema to be used for the adapter.
        :return:
        """

        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'IP Address',
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
                }
            ],
            'required': [
                'domain',
                'username',
                'password'
            ],
            'type': 'array'
        }

    def _create_wifi_device(self, device_raw):
        device = self._new_device_adapter()
        if not device_raw.get('ID') and not device_raw.get('MAC'):
            logger.warning(f'Bad device with no ID {device_raw}')
            return None
        device.id = (str(device_raw.get('ID')) or '') + '_' + (device_raw.get('MAC') or '')
        try:
            mac = device_raw.get('MAC')
            if not mac:
                mac = None
            ips = device_raw.get('IPAddress').split(',') if device_raw.get('IPAddress') else None
            if mac or ips:
                device.add_nic(mac, ips)
        except Exception:
            logger.exception(f'Problem getting nic for {device_raw}')
        device.node_id = device_raw.get('NodeID')
        device.wifi_display_name = device_raw.get('DisplayName')
        device.ssid = device_raw.get('SSID')
        device.wifi_name = device_raw.get('Name')
        device.description = device_raw.get('Description')
        device.instance_type = device_raw.get('InstanceType')
        try:
            device.last_update = parse_date(device_raw.get('LastUpdate'))
            device.first_update = parse_date(device_raw.get('FirstUpdate'))
        except Exception:
            logger.exception(f'Problem getting updates time for {device_raw}')
        device.set_raw(device_raw)
        return device

    def _create_dhcp_device(self, device_raw):
        device = self._new_device_adapter()
        if not device_raw.get('MAC') and not device_raw.get('DisplayName'):
            logger.debug(f'Bad device with no mac {device_raw}')
            return None
        device.id = (device_raw.get('MAC') or '') + '_' + (device_raw.get('DisplayName') or '')
        ips = [device_raw.get('IPAddress')] if device_raw.get('IPAddress') else None
        device.hostname = device_raw.get('DhcpClientName')
        device.add_nic(mac=device_raw.get('MAC'), ips=ips)
        if device_raw.get('Status') != 1:
            return None
        device.description = device_raw.get('Description')
        device.set_raw(device_raw)
        return device

    def _create_lan_device(self, device_raw):
        device = self._new_device_adapter()
        if not device_raw.get('MACAddress'):
            logger.warning(f'Bad device with no ID {device_raw}')
            return None
        device.id = 'lan' + '_' + (str(device_raw.get('NodeID')) or '') + '_' + (device_raw.get('MACAddress') or '')
        try:
            mac = device_raw.get('MACAddress')
            if not mac:
                mac = None
            ips = device_raw.get('IPAddress').split(',') if device_raw.get('IPAddress') else None
            if mac or ips:
                device.add_nic(mac, ips)
        except Exception:
            logger.exception(f'Problem getting nic for {device_raw}')
        device.node_id = device_raw.get('NodeID')
        device.lan_display_name = device_raw.get('DisplayName')
        device.lan_name = device_raw.get('HostName')
        device.description = device_raw.get('Description')
        device.connected_to = device_raw.get('ConnectedTo')
        device.connection_type_name = device_raw.get('ConnectionTypeName')
        device.port_number = device_raw.get('PortNumber')
        device.port_name = device_raw.get('PortName')
        device.solar_vlan = device_raw.get('VLAN')
        device.set_raw(device_raw)
        return device

    def _create_node_device(self, raw_device_data):
        try:
            device = self._new_device_adapter()
            # NodeID is the unique identifier over time
            id_check = raw_device_data.get('NodeID')
            if not id_check:
                logger.error(f'ID coming from Solarwinds does not have an ID on device {raw_device_data}')
                return None

            device.id = str(id_check)
            device.node_id = device.id
            device.name = raw_device_data.get('NodeName')
            device.description = raw_device_data.get('Description')
            available_memory_gb = None
            used_memory_gb = None
            try:
                if raw_device_data.get('MemoryAvailable'):
                    available_memory_bytes = float(raw_device_data.get('MemoryAvailable'))
                    available_memory_gb = available_memory_bytes / (1024 ** 3)
                    device.free_physical_memory = available_memory_gb
            except Exception:
                logger.exception(f'No value for the float for {raw_device_data}')
            try:
                if raw_device_data.get('MemoryUsed'):
                    used_memory_bytes = float(raw_device_data.get('MemoryUsed'))
                    used_memory_gb = used_memory_bytes / (1024 ** 3)
            except Exception:
                logger.exception(f'No value for the float for {raw_device_data}')

            try:
                if available_memory_gb and used_memory_gb:
                    device.total_physical_memory = available_memory_gb + used_memory_gb
            except Exception:
                logger.exception(f'Either memory used or available memory does not exist in {raw_device_data}')

            device.physical_memory_percentage = raw_device_data.get('PercentMemoryUsed')
            device.figure_os(raw_device_data.get('NodeDescription'))
            try:
                if raw_device_data.get('CPUCount'):
                    device.add_cpu(cores=int(raw_device_data.get('CPUCount')))
            except Exception:
                logger.exception(f'Either no value or illegal cast to integer for {raw_device_data}')
            device.uri = raw_device_data.get('Uri')
            device.ip_address_guid = raw_device_data.get('IPAddressGUID')

            mac_addresses = raw_device_data.get('MacAddresses') or []
            ip_address = raw_device_data.get('IPAddress') or []
            device.add_ips_and_macs(mac_addresses, ip_address)
            sw_list = raw_device_data.get('sw_list')
            if sw_list and isinstance(sw_list, list):
                for sw_data in sw_list:
                    try:
                        device.add_installed_software(name=sw_data[0],
                                                      version=sw_data[1],
                                                      publisher=sw_data[2])
                    except Exception:
                        logger.exception(f'Problem adding sw data to {raw_device_data}')
            device.software_hardware_makeup = raw_device_data.get('NodeDescription')
            device.location = raw_device_data.get('Location')
            device.set_raw(raw_device_data)
            return device
        except Exception:
            logger.exception(f'Got exception for raw_device_data: {raw_device_data}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Parses through the raw device list and creates new devices
        to be displayed on the Axonius site.
        :param raw_data: the list of devices that the system patrols
        :return:
        """
        for raw_device_data, device_type in iter(devices_raw_data):
            device = None
            if device_type == 'node':
                device = self._create_node_device(raw_device_data)
            elif device_type == 'wifi':
                device = self._create_wifi_device(raw_device_data)
            elif device_type == 'lan':
                device = self._create_lan_device(raw_device_data)
            elif device_type == 'dhcp':
                device = self._create_dhcp_device(raw_device_data)
            if device:
                yield device

        logger.info('Finished parsing all of the raw devices')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'fetch_ipam',
                    'title': 'Fetch IPAM',
                    'type': 'bool'
                }
            ],
            'required': [
                'fetch_ipam'
            ],
            'pretty_name': 'Solarwinds Orion Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'fetch_ipam': True
        }

    def _on_config_update(self, config):
        self.__fetch_ipam = config['fetch_ipam']
