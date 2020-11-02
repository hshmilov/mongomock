import logging

from axonius.adapter_base import AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, ASYNC_REQUESTS_DEFAULT_CHUNK_SIZE
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapterVlan
from axonius.mixins.configurable import Configurable
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.parsing import get_manufacturer_from_mac, int_or_none
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import format_ip
from infoblox_netmri_adapter.connection import InfobloxNetmriConnection
from infoblox_netmri_adapter.client_id import get_client_id
from infoblox_netmri_adapter.structures import InfobloxNetmriDeviceInstance, VLAN

logger = logging.getLogger(f'axonius.{__name__}')


class InfobloxNetmriAdapter(ScannerAdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(InfobloxNetmriDeviceInstance):
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
        connection = InfobloxNetmriConnection(domain=client_config['domain'],
                                              verify_ssl=client_config['verify_ssl'],
                                              https_proxy=client_config.get('https_proxy'),
                                              username=client_config['username'],
                                              password=client_config['password'])
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list(async_chunks=self.__async_chunks)

    @staticmethod
    # pylint: disable=arguments-differ
    def _query_users_by_client(client_name, client_data):
        """
        Get all users from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_user_list()

    @staticmethod
    def _clients_schema():
        """
        The schema InfobloxNetmriAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Infoblox NetMRI domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User name',
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
                    'title': 'HTTPS proxy',
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

    # pylint: disable=too-many-statements
    @staticmethod
    def _fill_infoblox_netmri_device_fields(device_raw: dict, device: MyDeviceAdapter):

        def parse_int(value):
            if value is None:
                return None
            try:
                return int(value)
            except Exception as e:
                logger.warning(f'Failed to parse {value} as integer! Got {str(e)}')
                return None

        def parse_bool(value):
            if isinstance(value, bool):
                return value
            return None

        try:
            device.extra_info = device_raw.get('DeviceAddlInfo')
            device.netbios_name = device_raw.get('DeviceNetBIOSName')
            device.device_type = device_raw.get('DeviceType')
            device.unique_key = device_raw.get('DeviceUniqueKey')
            device.snmp_sysdescr = device_raw.get('DeviceSysDescr')
            device.snmp_syslocation = device_raw.get('DeviceSysLocation')
            device.snmp_sysname = device_raw.get('DeviceSysName')
            device.dns_name = device_raw.get('DeviceDNSName')
            device.rev_end_time = parse_date(device_raw.get('DeviceEndTime'))
            device.rev_start_time = parse_date(device_raw.get('DeviceStartTime'))
            device.assurance = parse_int(device_raw.get('DeviceAssurance'))
            device.collector = parse_int(device_raw.get('DataSourceID'))
            device.parent_id = parse_int(device_raw.get('ParentDeviceID'))
            device.mgmt_server_id = parse_int(device_raw.get('MgmtServerDeviceID'))
            device.virtual_net_id = parse_int(device_raw.get('VirtualNetworkID'))
            device.is_infra = parse_bool(device_raw.get('InfraDeviceInd'))
            device.is_network = parse_bool(device_raw.get('NetworkDeviceInd'))
            device.is_virtual = parse_bool(device_raw.get('VirtualInd'))

            vlans_raw = device_raw.get('extra_vlans')
            device.vlans = []
            if isinstance(vlans_raw, list):
                for vlan_raw in vlans_raw:
                    if not isinstance(vlan_raw, dict):
                        continue
                    vlan = VLAN()
                    vlan.name = vlan_raw.get('VlanName')
                    vlan.domain = vlan_raw.get('VTPDomain')
                    vlan.vlan_internal_id = int_or_none(vlan_raw.get('VlanID'))
                    vlan.vlan_member_internal_id = int_or_none(vlan_raw.get('VlanMemberID'))
                    vlan.vlan_type = vlan_raw.get('VlanType')
                    vlan.time_collected = parse_date(vlan_raw.get('VlanMemberTimestamp'))
                    vlan.base_bridge_address = vlan_raw.get('BaseBridgeAddress')
                    vlan.root_bridge_address = vlan_raw.get('RootBridgeAddress')
                    vlan.bridge_forward_delay = int_or_none(vlan_raw.get('StpBridgeForwardDelay'))
                    vlan.bridge_max_age = int_or_none(vlan_raw.get('StpBridgeMaxAge'))
                    vlan.bridge_member = parse_bool(vlan_raw.get('BridgeMemberInd'))
                    vlan.datasource_id = int_or_none(vlan_raw.get('DataSourceID'))
                    vlan.forward_delay = int_or_none(vlan_raw.get('StpForwardDelay'))
                    vlan.interface_id = int_or_none(vlan_raw.get('InterfaceID'))
                    vlan.max_age = int_or_none(vlan_raw.get('StpMaxAge'))
                    vlan.number_of_ports = int_or_none(vlan_raw.get('BaseNumPorts'))
                    vlan.priority = int_or_none(vlan_raw.get('StpPriority'))
                    vlan.protocol = int_or_none(vlan_raw.get('StpProtocolSpecification'))
                    vlan.state = vlan_raw.get('VlanState')
                    device.vlans.append(vlan)
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('DeviceID')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device_mac = device_raw.get('DeviceMAC') or None  # Can be output as empty string
            device_name = device_raw.get('DeviceName')

            new_device_id = device_id + '_'
            if device_name:
                new_device_id = new_device_id + device_name
            if not new_device_id.endswith('_'):
                new_device_id = new_device_id + '_'
            if device_mac:
                new_device_id = new_device_id + device_mac

            device.id = new_device_id
            if device_name != 'unknown':
                device.name = device_name
            if device_raw.get('DeviceDNSName') != 'unknown':
                device.hostname = device_raw.get('DeviceDNSName')
            device.device_model = device_raw.get('DeviceModel')
            device.first_seen = parse_date(device_raw.get('DeviceFirstOccurrenceTime'))
            device.last_seen = parse_date(device_raw.get('DeviceTimestamp'))
            device.device_manufacturer = device_raw.get('DeviceVendor') or device_raw.get('DeviceOUI')
            try:
                device.figure_os(device_raw.get('DeviceVersion'))
            except Exception:
                logger.warning(f'Failed to parse OS for {device_name}', exc_info=True)
            device.device_managed_by = device_raw.get('DeviceSysContact')

            ip_dotted = device_raw.get('DeviceIPDotted') or None  # can be an empty string
            device_ip = None
            if ip_dotted:
                device_ip = ip_dotted
            else:
                # If we failed to get a dotted IP, then either the server has a bug (which can happen!)
                # or there's no ip registered. So try to get a numeric IP.
                # They should be the same IP.
                try:
                    ip_numeric = int(device_raw.get('DeviceIPNumeric'))
                    device_ip = (format_ip(ip_numeric))
                except Exception:
                    logger.exception(f'Failed to find IP for {device_raw}')
            mac_manufacturer = get_manufacturer_from_mac(device_mac)
            if mac_manufacturer and 'paloalto' in mac_manufacturer.lower().replace(' ', ''):
                device.fw_ip = device_ip
            device.add_nic(device_mac, ips=[device_ip])

            vlans = []
            vlans_raw = device_raw.get('extra_vlans')
            if isinstance(vlans_raw, list):
                for vlan_raw in vlans_raw:
                    if not isinstance(vlan_raw, dict):
                        continue
                    vlan = DeviceAdapterVlan()
                    vlan.name = vlan_raw.get('VlanName')
                    vlans.append(vlan)

                device.add_nic(vlans=vlans)

            # Now parse specific fields
            self._fill_infoblox_netmri_device_fields(device_raw, device)
            device.set_raw(device_raw)

            return device
        except Exception:
            logger.exception(f'Problem with fetching Infoblox NetMRI Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching InfobloxNetmri Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Network]

    @classmethod
    def _db_config_schema(cls) -> dict:
        """
        Return the schema this class wants to have for the config
        """
        return {
            'items': [
                {
                    'name': 'async_chunks',
                    'type': 'integer',
                    'title': 'Number of requests in parallel'
                }
            ],
            'required': ['async_chunks'],
            'pretty_name': 'Infoblox NetMRI Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        """
        Return the default configuration for this class
        """
        return {
            'async_chunks': ASYNC_REQUESTS_DEFAULT_CHUNK_SIZE
        }

    def _on_config_update(self, config):
        """
        Virtual
        This is called on every inheritor when the config was updated.
        """
        self.__async_chunks = int_or_none(config.get('async_chunks')) or ASYNC_REQUESTS_DEFAULT_CHUNK_SIZE
