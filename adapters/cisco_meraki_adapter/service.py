import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter, SmartJsonClass
from axonius.utils.files import get_local_config_file
from axonius.fields import Field, ListField
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.devices.device_adapter import DeviceAdapterNetworkInterface, DeviceAdapterNeighbor, \
    DeviceAdapterVlan, ConnectionType
from cisco_meraki_adapter.connection import CiscoMerakiConnection
from cisco_meraki_adapter.consts import DEVICE_TYPE, CLIENT_TYPE, MDM_TYPE

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-instance-attributes
class AssociatedDeviceAdapter(SmartJsonClass):
    switch_port = Field(str, 'Switch Port')
    associated_device = Field(str, 'Associated Device')
    address = Field(str, 'Address')
    network_name = Field(str, 'Network Name')
    vlan = Field(str, 'Vlan')
    name = Field(str, 'Name')
    notes = Field(str, 'Notes')
    tags = Field(str, 'Tags')
    wan1_ip = Field(str, 'Wan1 IP')
    wan2_ip = Field(str, 'Wan2 IP')
    lan_ip = Field(str, 'Lan IP')
    public_ip = Field(str, 'Public IP')


class CiscoMerakiAdapter(AdapterBase):

    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        associated_user = Field(str, 'Associated User')
        device_type = Field(str, 'Device Type', enum=[DEVICE_TYPE, CLIENT_TYPE, MDM_TYPE])
        network_id = Field(str, 'Network Name')
        lng = Field(str, 'Lng')
        lat = Field(str, 'Lat')
        notes = Field(str, 'Notes')
        device_status = Field(str, 'Device Status')
        cisco_tags = ListField(str, 'Cisco Tags')
        address = Field(str, 'Address')
        dns_name = Field(str, 'DNS Name')
        associated_devices = ListField(AssociatedDeviceAdapter, 'Associated Devices')
        mdm_tags = ListField(str, 'Mobile Tags')
        ssid = Field(str, 'SSID')
        has_chrome_mdm = Field(bool, 'Has Chrome MDM')
        phone_number = Field(str, 'Phone Number')
        owner_username = Field(str, 'Owner Username')
        owner_email = Field(str, 'Owner Email')
        system_type = Field(str, 'System Type')
        is_rooted = Field(str, 'Is Rooted')
        imei = Field(str, 'IMEI')
        auto_tags = ListField(str, 'Auto Tags')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return client_config['CiscoMeraki_Domain']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('CiscoMeraki_Domain'))

    @staticmethod
    def get_connection(client_config):
        connection = CiscoMerakiConnection(domain=client_config['CiscoMeraki_Domain'],
                                           apikey=client_config['apikey'],
                                           verify_ssl=client_config['verify_ssl'],
                                           https_proxy=client_config.get('https_proxy'))
        with connection:
            pass
        return connection, client_config.get('vlan_exclude_list')

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['CiscoMeraki_Domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific CiscoMeraki domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a CiscoMeraki connection

        :return: A json with all the attributes returned from the CiscoMeraki Server
        """
        connection, vlan_exclude_list = client_data
        if not vlan_exclude_list:
            vlan_exclude_list = []
        else:
            vlan_exclude_list = vlan_exclude_list.split(',')
        with connection:
            for deivce_raw, device_type in connection.get_device_list():
                yield deivce_raw, device_type, vlan_exclude_list

    @staticmethod
    def _clients_schema():
        """
        The schema CiscoMerakiAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'CiscoMeraki_Domain',
                    'title': 'CiscoMeraki Domain',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'Apikey',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'vlan_exclude_list',
                    'title': 'VLAN Exclude List',
                    'type': 'string'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'CiscoMeraki_Domain',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _create_client_type_device(self, client_raw, client_id, vlan_exclude_list):
        try:
            client_raw['associated_devices'] = list(client_raw['associated_devices'])
            client_raw['ip'] = list(filter(lambda ip: isinstance(ip, str), client_raw['ip']))
            device = self._new_device_adapter()
            device.id = client_id
            device.associated_user = client_raw.get('user')
            device.device_type = CLIENT_TYPE
            mac_address = client_raw.get('mac')
            hostname = client_raw.get('mdnsName') or client_raw.get('dhcpHostname')
            if str(hostname).lower().endswith('.local'):
                hostname = str(hostname)[:-len('.local')]
            device.hostname = hostname
            if client_raw.get('mdnsName') and client_raw.get('dhcpHostname') and \
                    client_raw.get('mdnsName')[:5] == client_raw.get('dhcpHostname')[:5]:
                device.name = client_raw.get('dhcpHostname')
            try:
                ip_addresses = list(client_raw.get('ip'))
                if ip_addresses or mac_address:
                    device.add_nic(mac_address, ip_addresses)
            except Exception:
                logger.exception(f'Problem with fetching NIC in CiscoMeraki Client {client_raw}')
            device.description = client_raw.get('description')
            device.associated_devices = []
            found_regular_vlan = False
            found_exclude_vlan = False
            for associated_device, switch_port, address, network_name, vlan, name, notes,\
                tags, wan1_ip, wan2_ip, lan_ip, public_ip in \
                    client_raw['associated_devices']:
                try:
                    associated_device_object = AssociatedDeviceAdapter()
                    associated_device_object.switch_port = switch_port
                    associated_device_object.associated_device = associated_device
                    associated_device_object.address = address
                    associated_device_object.network_name = network_name
                    associated_device_object.vlan = vlan
                    if vlan:
                        if str(vlan) in vlan_exclude_list:
                            found_exclude_vlan = True
                        else:
                            found_regular_vlan = True
                    associated_device_object.name = name
                    associated_device_object.notes = notes
                    associated_device_object.tags = tags
                    associated_device_object.wan1_ip = wan1_ip
                    associated_device_object.wan2_ip = wan2_ip
                    associated_device_object.lan_ip = lan_ip
                    associated_device_object.public_ip = public_ip
                    device.associated_devices.append(associated_device_object)

                    connected_device = DeviceAdapterNeighbor()
                    connected_device.remote_name = name
                    connected_device.connection_type = ConnectionType.Direct.name
                    iface = DeviceAdapterNetworkInterface(name=network_name)
                    vlan_tagid = None
                    vlan_name = None
                    try:
                        vlan_tagid = int(vlan)
                    except Exception:
                        vlan_name = vlan
                    iface.vlan_list.append(DeviceAdapterVlan(tagid=vlan_tagid, name=vlan_name))
                    connected_device.remote_ifaces.append(iface)
                    device.connected_devices.append(connected_device)
                except Exception:
                    logger.exception(f'Problem adding associated device'
                                     f' {associated_device} with port {switch_port}')
            device.set_raw(client_raw)
            if found_exclude_vlan and not found_regular_vlan:
                return None
            return device
        except Exception:
            logger.exception(f'Problem with fetching CiscoMeraki Client {client_raw}')
            return None

    def _create_device_type_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_serial = device_raw.get('serial')
            if not device_serial:
                logger.warning(f'Bad device with no serial {device_raw}')
                return None
            device.device_serial = device_serial
            mac_address = device_raw.get('mac')
            if not mac_address:
                mac_address = None
            device.id = device.device_serial
            device.device_type = DEVICE_TYPE
            device.device_model = device_raw.get('model')
            device.name = device_raw.get('name')
            ip_addresses = []
            if device_raw.get('lanIp'):
                ip_addresses.append(device_raw.get('lanIp'))
            if device_raw.get('wan1Ip'):
                ip_addresses.append(device_raw.get('wan1Ip'))
            if device_raw.get('wan2Ip'):
                ip_addresses.append(device_raw.get('wan2Ip'))
            if not ip_addresses:
                ip_addresses = None
            if mac_address or ip_addresses:
                device.add_nic(mac_address, ip_addresses)
            # These values are the geo location of the Cisco Meraki device
            device.lat = device_raw.get('lat')
            device.lng = device_raw.get('lng')
            device.address = device_raw.get('address')
            device.network_id = device_raw.get('network_name')
            device.notes = device_raw.get('notes')
            if device_raw.get('tags') and isinstance(device_raw.get('tags'), str):
                device.cisco_tags = device_raw.get('tags').split(',')
            device.adapter_properties = [AdapterProperty.Network.name, AdapterProperty.Manager.name]
            try:
                device_status = device_raw.get('device_status')
                device.add_public_ip(device_status.get('publicIp'))
                device.device_status = device_status.get('status')
            except Exception:
                logger.exception('Problem with status')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching CiscoMeraki Device {device_raw}')
            return None

    @staticmethod
    def _add_client_raw_to_clients_dict(clients_id_dict, client_raw):
        try:
            for key in client_raw:
                if client_raw[key] is not None:
                    client_raw[key] = str(client_raw[key])
            device_id = client_raw.get('mac') or client_raw.get('id') or ''
            if not device_id:
                logger.info(f'No ID (MAC) for device: {client_raw}')
                return
            # fix ips
            if 'ip' in client_raw and client_raw['ip']:
                client_raw['ip'] = set(client_raw['ip'].split(','))
            else:
                client_raw['ip'] = set()

            if device_id not in clients_id_dict:
                clients_id_dict[device_id] = client_raw
                clients_id_dict[device_id]['associated_devices'] = set()
            clients_id_dict[device_id]['ip'].union(client_raw['ip'])
            clients_id_dict[device_id]['associated_devices'].add(
                (client_raw.get('associated_device'), client_raw.get('switchport'),
                 client_raw.get('address'), client_raw.get('network_name'),
                 client_raw.get('vlan'), client_raw.get('name'),
                 client_raw.get('notes'), client_raw.get('tags'),
                 client_raw.get('wan1Ip'), client_raw.get('wan2Ip'), client_raw.get('lanIp'),
                 client_raw.get('public_ip')))
        except Exception:
            logger.exception(f'Problem with fetching CiscoMeraki Client {client_raw}')

    def _create_mdm_type_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('name') or '')
            device.name = device_raw.get('name')
            try:
                if device_raw.get('tags') and isinstance(device_raw.get('tags'), list):
                    device.mdm_tags = device_raw.get('tags')
            except Exception:
                logger.exception(f'Problem getting tags for {device_raw}')
            try:
                if device_raw.get('autoTags') and isinstance(device_raw.get('autoTags'), list):
                    device.auto_tags = device_raw.get('autoTags')
            except Exception:
                logger.exception(f'Problem getting auto tags for {device_raw}')
            device.ssid = device_raw.get('ssid')
            device.uuid = device_raw.get('uuid')
            device.device_model = device_raw.get('systemModel')
            device.adapter_properties = [AdapterProperty.Agent.name]
            device.physical_location = device_raw.get('location')
            device.bios_version = device_raw.get('biosVersion')
            try:
                device.figure_os(device_raw.get('osName'))
            except Exception:
                logger.exception(f'Problem gettins os for {device_raw}')
            device.device_serial = device_raw.get('serialNumber')
            try:
                mac = device_raw.get('wifiMac')
                if not mac:
                    mac = None
                ip = device_raw.get('ip')
                if ip:
                    ip = ip.split(',')
                else:
                    ip = None
                if mac or ip:
                    device.add_nic(mac, ip)
            except Exception:
                logger.exception(f'Problem gettins mac for {device_raw}')
            device.has_chrome_mdm = device_raw.get('hasChromeMdm')
            device.add_public_ip(device_raw.get('publicIp'))
            device.owner_username = device_raw.get('ownerUsername')
            device.owner_email = device_raw.get('ownerEmail')
            device.is_rooted = device_raw.get('isRooted')
            device.imei = device_raw.get('imei')
            device.system_type = device_raw.get('systemType')
            if device_raw.get('lastUser'):
                device.last_used_users = device_raw.get('lastUser')

            try:
                device.last_seen = datetime.datetime.fromtimestamp(device_raw.get('lastConnected'))
            except Exception:
                logger.exception(f'Problem getting last seen for {device_raw}')
            device.phone_number = device_raw.get('phoneNumber')
            device.network_id = device_raw.get('network_name')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching MDM Device {device_raw}')
            return None

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks, arguments-differ
    def _parse_raw_data(self, devices_clients_vlan_exclude):
        vlan_exclude_list_global = None
        clients_id_dict = dict()
        for deivce_raw, device_type, vlan_exclude_list in devices_clients_vlan_exclude:
            vlan_exclude_list_global = vlan_exclude_list
            if device_type == DEVICE_TYPE:
                device = self._create_device_type_device(deivce_raw)
                if device:
                    yield device
            elif device_type == CLIENT_TYPE:
                self._add_client_raw_to_clients_dict(client_raw=deivce_raw, clients_id_dict=clients_id_dict)
            if device_type == MDM_TYPE:
                device = self._create_mdm_type_device(deivce_raw)
                if device:
                    yield device
        for client_id, client_raw in clients_id_dict.items():
            device = self._create_client_type_device(client_raw, client_id, vlan_exclude_list_global)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
