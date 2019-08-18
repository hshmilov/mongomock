import datetime
import itertools
import logging
from collections import defaultdict
from enum import Enum, auto
from functools import reduce

from axonius.clients.cisco.constants import OIDS, get_oid_name
from axonius.clients.cisco.port_security import PortSecurityInterface, SecureMacAddressEntry
from axonius.clients.cisco.port_access import PortAccessEntity

from axonius.devices.device_adapter import (
    AdapterProperty,
    ConnectionType,
    DeviceAdapter,
    DeviceAdapterNeighbor,
    DeviceAdapterNetworkInterface,
    Field,
)

logger = logging.getLogger(f'axonius.{__name__}')


class FetchProto(Enum):
    ARP = auto()
    CDP = auto()
    DHCP = auto()
    CLIENT = auto()
    PRIME_CLIENT = auto()
    PRIME_WIFI_CLIENT = auto()


class CiscoDevice(DeviceAdapter):
    # Fetch protocol refers to the way we discover new devices
    # (by querying arp, cdp, dhcp tables, or by adding the client itself).
    fetch_proto = Field(str, 'Fetch Protocol', enum=FetchProto)
    reachability = Field(str, 'Reachability')
    ad_domainName = Field(str, 'AD Domain Name')
    ap_ip_address = Field(str, 'AP IP Address')
    ap_mac_address = Field(str, 'AP MAC Address')
    ap_name = Field(str, 'AP Name')
    auth_algo = Field(str, 'Authentication Algorithm')
    nac_state = Field(str, 'NAC State')
    wireless_vlan = Field(str, 'Wireless Vlan')
    association_time = Field(datetime.datetime, 'Association Time')
    device_type = Field(str, 'Device Type')
    ssid = Field(str, 'SSID')


class AbstractCiscoClient:
    """ Abstract class for cisco's clients.
        each function must raise ClientConnectionException for creds errors """

    def __init__(self):
        self._in_context = False

    def __enter__(self):
        """ entry that connect to the cisco device. """
        self._in_context = True
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """ exit that to the cisco device. """
        self._in_context = False

    @staticmethod
    def get_device_type():
        raise NotImplementedError()

    @staticmethod
    def test_reachability(host, port):
        raise NotImplementedError()

    def is_valid(self, should_log_exception=True):
        """
             wrapper for validate_connection, return bool instead of exception.
        """

        try:
            self.validate_connection()
        except Exception as e:
            if should_log_exception:
                logger.exception(e)
            else:
                host = ''
                if hasattr(self, '_ip'):
                    host = self._ip
                if hasattr(self, 'host'):
                    host = self.host
                logger.info(f'{self} - unable to connect {host}: error: {str(e)}')
            return False
        return True

    def validate_connection(self):
        """
            validate that that we can communicate with the client using the given creds
            raise indicative Exception if we failed to.
        """
        raise NotImplementedError()

    def _query_arp_table(self):
        """ This function should be overwritten by heir."""
        raise NotImplementedError()

    def _query_dhcp_leases(self):
        """ This function should be overwritten by heir."""
        raise NotImplementedError()

    def _query_cdp_table(self):
        """ This function should be overwritten by heir."""
        raise NotImplementedError()

    def query_arp_table(self):
        assert self._in_context
        return self._query_arp_table()

    def query_dhcp_leases(self):
        assert self._in_context
        return self._query_dhcp_leases()

    def query_cdp_table(self):
        assert self._in_context
        return self._query_cdp_table()

    def query_basic_info(self):
        assert self._in_context
        return self._query_basic_info()

    def query_all(self):
        assert self._in_context

        for callback in [self.query_arp_table, self.query_dhcp_leases, self.query_cdp_table, self.query_basic_info]:
            try:
                data = callback()
                if data:
                    yield data
            except Exception:
                logger.exception(f'Exception while querying {callback}')


class AbstractCiscoData:
    """Abstract class for cisco data.
        each cisco client query should return CiscoData class,
        that will be yielded in _query_device_by_client.
        then in _parse_raw_data we can call get_devices """

    def __init__(self, raw_data, received_from=None):
        self._raw_data = raw_data
        self.parsed_data = None
        self.received_from = received_from

    def _parse(self) -> dict:
        raise NotImplementedError()

    def get_parsed_data(self) -> list:
        if not self.parsed_data:
            instances = list(self._parse())
            for instance in instances:
                # XXX: Kinda hacky fix the remote_iface
                if self.received_from and self.get_protocol_type():
                    instance['connected_devices'] = [
                        {
                            'name': self.received_from,
                            'iface': instance.get('remote_iface', ''),
                            'type': self.get_protocol_type(),
                        }
                    ]
            self.parsed_data = instances
        return self.parsed_data

    @staticmethod
    def _get_id(instance):
        return instance.get('mac')

    # pylint: disable=too-many-locals
    @staticmethod
    def _handle_ifaces(new_device, instance):
        interface_field = get_oid_name(OIDS.interface)
        port_security_field = get_oid_name(OIDS.port_security)
        port_access_field = get_oid_name(OIDS.port_access)

        ip_field = get_oid_name(OIDS.ip)
        for iface in instance[interface_field].values():
            ip_list = []
            netmask_list = []

            if ip_field in iface:
                ip_list = [x.get('address') for x in iface[ip_field] if x.get('address')]
                netmask_list = [x.get('net-mask') for x in iface[ip_field] if x.get('net-mask')]
                netmask_list = list(map('/'.join, zip(ip_list, netmask_list)))

            name = iface.get('description')
            operational_status = iface.get('operation-status')
            admin_status = iface.get('admin-status')
            mac = iface.get('mac')
            speed = iface.get('speed')
            mtu = iface.get('mtu')

            new_device.add_nic(
                mac=iface.get('mac'),
                name=iface.get('description'),
                operational_status=operational_status,
                admin_status=admin_status,
                speed=speed,
                mtu=mtu,
                ips=ip_list,
                subnets=netmask_list,
            )

            if port_security_field in iface and iface[port_security_field].get('enabled'):
                port_security = iface[port_security_field]
                entries = []
                for mac, attributes in iface[port_security_field].get('entries', {}).items():
                    entry = SecureMacAddressEntry(
                        mac_address=mac, type=attributes.get('type'), remaining_age_time=attributes.get('remaining_age')
                    )
                    entries.append(entry)

                port_security_class = PortSecurityInterface(
                    name=iface.get('description'),
                    status=port_security.get('status'),
                    sticky=port_security.get('sticky'),
                    max_addr=port_security.get('max_addr'),
                    violation_action=port_security.get('violation_action'),
                    violation_count=port_security.get('violation_count'),
                    entries=entries,
                )
                new_device.port_security.append(port_security_class)

            if port_access_field in iface:
                port_access = iface[port_access_field]
                port_access_class = PortAccessEntity(
                    name=iface.get('description'),
                    port_mode=port_access.get('port_mode'),
                    operation_vlan_type=port_access.get('operation_vlan_type'),
                    guest_vlan_number=port_access.get('guest_vlan_number'),
                    auth_fail_vlan_number=port_access.get('auth_fail_vlan_number'),
                    operation_vlan_number=port_access.get('operation_vlan_number'),
                    shutdown_timeout_enabled=port_access.get('shutdown_timeout_enabled'),
                    auth_fail_max_attempts=port_access.get('auth_fail_max_attempts'))
                new_device.port_access.append(port_access_class)

    @staticmethod
    def _handle_connected(new_device, instance):
        for raw_connected_device in instance['connected_devices']:
            neighbor_device = DeviceAdapterNeighbor()
            neighbor_device.remote_name = raw_connected_device['name']
            neighbor_device.connection_type = raw_connected_device['type']
            if raw_connected_device['iface']:
                interface = DeviceAdapterNetworkInterface()
                interface.name = raw_connected_device['iface']
                neighbor_device.remote_ifaces.append(interface)
            new_device.connected_devices.append(neighbor_device)

    def _get_devices(self, instance: dict, create_device_callback):
        """ This function gets instances (dicts that hold the "raw data")
            from _parse implemenataion of each CiscoData class
            and convert them to axonius devices.
            Each instance might hold different fields,
            so we assume that some or all fields might be missing.
            This function defines the instance structure.
        """
        interface_field = get_oid_name(OIDS.interface)
        id_ = self._get_id(instance)
        if id_ is None:
            logger.warning(f'Unable to create id_ for instace {instance}')
            return None

        new_device = create_device_callback()

        new_device.id = id_

        # XXX: we don't need ifaces and iface, there is duplication in the structure
        if any(['ip' in instance, 'mac' in instance, 'iface' in instance]):
            ips = [instance.get('ip')] if instance.get('ip') else []
            new_device.add_nic(mac=instance.get('mac'), name=instance.get('iface'), ips=ips)

        if interface_field in instance:
            self._handle_ifaces(new_device, instance)

        if 'connected_devices' in instance:
            self._handle_connected(new_device, instance)

        new_device.hostname = instance.get('hostname')
        new_device.device_model = instance.get('device_model')

        new_device.figure_os(instance.get('device_model'))
        new_device.figure_os(instance.get('version'))
        new_device.figure_os(instance.get('os'))
        new_device.os.build = instance.get('version')
        new_device.device_serial = instance.get('device_serial')

        if 'base_mac' in instance:
            new_device.add_nic(name='base-mac', mac=instance.get('base_mac'))

        if 'related_ips' in instance:
            new_device.set_related_ips(instance['related_ips'])

        if 'uptime' in instance:
            new_device.set_boot_time(uptime=datetime.timedelta(seconds=int(instance['uptime']) / 100.0))

        # XXX: the real raw data is self._raw_data
        # but it isn't a dict so for now we only save the instance - which must be a dict
        new_device.set_raw(instance)
        return new_device

    def get_devices(self, create_device_callback):
        for instance in self.get_parsed_data():
            # without mac we can not create device
            try:
                new_device = self._get_devices(instance, create_device_callback)
                if new_device:
                    yield new_device
            except Exception:
                logger.exception('Exception while getting devices')

    def get_protocol_type(self):
        """ this function should return what kind of protocol we are parsing """
        raise NotImplementedError()


class BasicInfoData(AbstractCiscoData):
    def _parse(self) -> dict:
        raise NotImplementedError()

    def _get_id(self, instance):
        id_ = '_'.join(filter(None, ['basic_info',
                                     instance.get('hostname', ''),
                                     instance.get('base_mac'),
                                     instance.get('device_serial')]))
        if id_ == 'basic_info':
            return None
        return id_

    def _get_devices(self, instance, create_device_callback):
        device = super()._get_devices(instance, create_device_callback)
        if device:
            device.fetch_proto = FetchProto.CLIENT.name
            device.adapter_properties = [AdapterProperty.Network.name, AdapterProperty.Manager.name]
            # we are running on the endpoint, so the last seen is right now
            device.last_seen = datetime.datetime.utcnow()
        return device

    def get_protocol_type(self):
        # we dont have protocol type since we are bringing the device itself
        return ''


class ArpCiscoData(AbstractCiscoData):
    def _parse(self) -> dict:
        raise NotImplementedError()

    def _get_id(self, instance):
        return 'arp_' + instance.get('mac') if instance.get('mac') else None

    def _get_devices(self, instance, create_device_callback):
        device = super()._get_devices(instance, create_device_callback)
        if device:
            device.fetch_proto = FetchProto.ARP.name
            device.adapter_properties = [AdapterProperty.Network.name]

        return device

    def get_protocol_type(self):
        return ConnectionType.Indirect.name


class DhcpCiscoData(AbstractCiscoData):
    def _parse(self) -> dict:
        raise NotImplementedError()

    def _get_id(self, instance):
        mac = instance.get('mac')
        iface = instance.get('iface')
        id_ = 'dhcp'

        if not mac:
            return None

        id_ += '_' + mac

        if iface:
            id_ += '_' + iface

        return id_

    def _get_devices(self, instance, create_device_callback):
        device = super()._get_devices(instance, create_device_callback)
        if device:
            device.fetch_proto = FetchProto.DHCP.name
        return device

    def get_protocol_type(self):
        return ConnectionType.Indirect.name


class CdpCiscoData(AbstractCiscoData):
    def _parse(self) -> dict:
        raise NotImplementedError()

    def _get_id(self, instance):
        hostname = instance.get('hostname')
        id_ = 'cdp'

        if not hostname:
            return None

        id_ += '_' + hostname

        return id_

    def _get_devices(self, instance, create_device_callback):
        device = super()._get_devices(instance, create_device_callback)
        if device:
            device.fetch_proto = FetchProto.CDP.name
            device.adapter_properties = [AdapterProperty.Network.name]
        return device

    def get_protocol_type(self):
        return ConnectionType.Direct.name


class InstanceParser:
    """ parse multiple instances of CiscoData, correlate and return devices
        This class exists because we need some way to correlate between arp table
        and cdp table """

    def __init__(self, instances):
        self._instances = [x for x in instances if x is not None]

    @staticmethod
    def _sort_instance_by_key(instances: list, key: str) -> dict:
        """ Sort by key, if we dont have key put in unique number (using counter) """
        result = defaultdict(list)
        counter = itertools.count()

        for instance in instances:
            for parsed_data in instance.get_parsed_data():
                if parsed_data.get(key):
                    result[parsed_data.get(key)].append(parsed_data)
                else:
                    result[next(counter)].append(parsed_data)
        return result

    @staticmethod
    def _correlate_cdp_arp(instances):
        """ for each cdp and other device that came from the same machine and has the same ip,
            we want to copy the mac address from the other device to cdp """

        cdp_instances = set((x for x in instances if isinstance(x, CdpCiscoData)))
        other_instances = set(instances) - cdp_instances

        # try to find correlation in ip
        # and connected_device name (we only have now connected_device in this phase for sure)

        cdp_jsons = itertools.chain.from_iterable(map(lambda instance: instance.get_parsed_data(), cdp_instances))
        other_jsons = itertools.chain.from_iterable(map(lambda instance: instance.get_parsed_data(), other_instances))

        for cdp, other in itertools.product(cdp_jsons, other_jsons):
            try:
                if cdp.get('ip') != other.get('ip'):
                    continue

                if not (cdp.get('connected_devices') and other.get('connected_devices')):
                    continue

                if cdp.get('connected_devices')[0].get('name') != other.get('connected_devices')[0].get('name'):
                    continue

                if cdp.get('mac') or not other.get('mac'):
                    continue

                # found correlation
                cdp['mac'] = other['mac']

            except Exception:
                logger.exception(f'Error while tring to correlate cdp: {cdp}, {other}')
        return instances

    @staticmethod
    def _merge_cdps(cdps: list):
        assert len(cdps) >= 1, f'cdps must have at least one instance in list, got {cdps}'

        interface_field = get_oid_name(OIDS.interface)
        result = CdpCiscoData(raw_data='')
        counter = itertools.count()

        first_cdp = cdps[0]

        parsed_data = {}
        parsed_data['hostname'] = first_cdp.get('hostname')
        parsed_data['version'] = first_cdp.get('version')
        parsed_data['device_model'] = first_cdp.get('device_model')
        parsed_data[interface_field] = {}
        parsed_data['connected_devices'] = []

        for cdp in cdps:
            try:
                if 'iface' in cdp:
                    interface = {'description': cdp['iface']}
                    interface['mac'] = cdp.get('mac')
                    if 'ip' in cdp:
                        interface['ips'] = [{'address': cdp['ip']}]
                    parsed_data[interface_field][next(counter)] = interface

                if 'connected_devices' in cdp:
                    parsed_data['connected_devices'] += cdp['connected_devices']
            except Exception:
                logger.exception(f'Error while merging cdps {cdp}')

        result.parsed_data = [parsed_data]
        return result

    def _correlate_cdp_cdp(self, instances):
        """ we want to find all cdps with the same name and merge them """
        cdp_instances = set((x for x in instances if isinstance(x, CdpCiscoData)))
        other_instances = set(instances) - cdp_instances

        cdp_dict = self._sort_instance_by_key(cdp_instances, 'hostname')

        correlated_cdp_instances = [self._merge_cdps(correlate_list) for correlate_list in cdp_dict.values()]
        return list(other_instances) + correlated_cdp_instances

    @staticmethod
    def _merge_arps(arps: list):
        assert len(arps) >= 1, f'arps must have at least one instance in list, got {arps}'

        result = ArpCiscoData(raw_data='')
        parsed_data = {}

        parsed_data['mac'] = arps[0].get('mac')
        parsed_data['related_ips'] = []
        parsed_data['connected_devices'] = []

        for arp in arps:
            if arp.get('ip'):
                parsed_data['related_ips'].append(arp.get('ip'))

            if 'connected_devices' in arp:
                if arp['connected_devices'] not in parsed_data['connected_devices']:
                    parsed_data['connected_devices'] += arp['connected_devices']

        result.parsed_data = [parsed_data]
        return result

    def _correlate_arp_arp(self, instances):
        """ find arp with the same macs and correlate then """
        arp_instances = set((x for x in instances if isinstance(x, ArpCiscoData)))
        other_instances = set(instances) - arp_instances

        arp_dict = self._sort_instance_by_key(arp_instances, 'mac')

        correlated_arp_instances = [self._merge_arps(correlate_list) for correlate_list in arp_dict.values()]
        return list(other_instances) + correlated_arp_instances

    def get_devices(self, create_device_callback):
        # first we want to fix cdp, then merge cdp, then merge arps
        funcs = (self._correlate_cdp_arp, self._correlate_cdp_cdp, self._correlate_arp_arp)

        # apply each function on instances
        self._instances = reduce(lambda instances, func: func(instances), funcs, self._instances)

        # run .get_devices() for each instance and chain the results to one iterable
        return itertools.chain.from_iterable((x.get_devices(create_device_callback) for x in self._instances))
