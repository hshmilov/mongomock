import logging
import itertools

from collections import defaultdict

from axonius.devices.device_adapter import (DeviceAdapter, Field,
                                            DeviceAdapterNeighbor, DeviceAdapterNetworkInterface)

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoDevice(DeviceAdapter):
    # Fetch protocol refers to the way we discover new devices
    # (by querying arp, cdp, dhcp tables, or by adding the client itself).
    fetch_proto = Field(str, 'Fetch Protocol', enum=['ARP', 'CDP', 'DHCP', 'CLIENT'])
    reachability = Field(str, 'Reachability')


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

    def is_valid(self):
        """
             wrapper for validate_connection, return bool instead of exception.
        """

        try:
            self.validate_connection()
        except Exception as e:
            logger.exception(e)
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
                    instance['connected_devices'] = [{'name': self.received_from,
                                                      'iface': instance.get('remote_iface', ''),
                                                      'type': self.get_protocol_type(),
                                                      }]
            self.parsed_data = instances
        return self.parsed_data

    @staticmethod
    def _get_id(instance):
        return instance.get('mac')

    @staticmethod
    def _handle_ifaces(new_device, instance):
        for iface in instance['ifaces'].values():
            ip_list = []
            netmask_list = []

            if 'ips' in iface:
                ip_list = [x.get('address') for x in iface['ips'] if x.get('address')]
                netmask_list = [x.get('net-mask') for x in iface['ips'] if x.get('net-mask')]
                netmask_list = list(map('/'.join, zip(ip_list, netmask_list)))

            name = iface.get('description')
            operational_status = iface.get('operation-status')
            admin_status = iface.get('admin-status')
            mac = iface.get('mac')
            speed = iface.get('speed')
            mtu = iface.get('mtu')

            new_device.add_nic(mac=iface.get('mac'),
                               name=iface.get('description'),
                               operational_status=operational_status,
                               admin_status=admin_status, speed=speed, mtu=mtu,
                               ips=ip_list, subnets=netmask_list)

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

        if 'ifaces' in instance:
            self._handle_ifaces(new_device, instance)

        if 'connected_devices' in instance:
            self._handle_connected(new_device, instance)

        new_device.hostname = instance.get('hostname')
        new_device.device_model = instance.get('device_model')

        new_device.figure_os(instance.get('device_model'))
        new_device.os.build = instance.get('version')

        if 'related_ips' in instance:
            new_device.set_related_ips(instance['related_ips'])

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
        id_ = '_'.join(['basic_info', instance.get('hostname', '')])
        if id_ == 'basic_info':
            return None
        return id_

    def _get_devices(self, instance, create_device_callback):
        device = super()._get_devices(instance, create_device_callback)
        if device:
            device.fetch_proto = 'CLIENT'
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
            device.fetch_proto = 'ARP'

        return device

    def get_protocol_type(self):
        return 'Indirect'


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
            device.fetch_proto = 'DHCP'
        return device

    def get_protocol_type(self):
        return 'Indirect'


class CdpCiscoData(AbstractCiscoData):
    def _parse(self) -> dict:
        raise NotImplementedError()

    def _get_id(self, instance):
        mac = instance.get('mac')
        iface = instance.get('iface')
        id_ = 'cdp'

        if not mac:
            return None

        id_ += '_' + mac

        if iface:
            id_ += '_' + iface

        return id_

    def _get_devices(self, instance, create_device_callback):
        device = super()._get_devices(instance, create_device_callback)
        if device:
            device.fetch_proto = 'CDP'
        return device

    def get_protocol_type(self):
        return 'Direct'


class InstanceParser:
    """ parse multiple instances of CiscoData, correlate and return devices
        This class exists because we need some way to correlate between arp table
        and cdp table """

    def __init__(self, instances):
        self._instances = list(filter(lambda x: x is not None, instances))

    def get_devices(self, create_device_callback):
        cdp_instance = list(filter(lambda x: isinstance(x, CdpCiscoData), self._instances))
        arp_instance = list(filter(lambda x: isinstance(x, ArpCiscoData), self._instances))

        # For each cdp device - check if we also see it in any other table (arp and dhcp)
        # if we do - copy mac for correlation
        if cdp_instance:
            cdp_instance = cdp_instance[0]

            # XXX: arp throws iface
            # XXX: cdp neighbors doesn't correlate when one have empty ip
            for cdp_data in cdp_instance.get_parsed_data():
                try:
                    if cdp_data.get('mac'):
                        continue

                    filtered = filter(lambda x: not isinstance(x, CdpCiscoData), self._instances)
                    for other_data in sum(list(map(lambda x: x.get_parsed_data(), filtered)), []):
                        if cdp_data.get('ip') == other_data.get('ip'):
                            cdp_data['mac'] = other_data.get('mac')
                            break
                except Exception:
                    logger.exception('Error while tring to correlate cdp')

        # For each arp device - we want to set ip as realted_ip if we haven't seen it in any other protocol
        if arp_instance:
            arp_instance = arp_instance[0]

            try:
                mac_ip_correlation = defaultdict(set)
                for data in arp_instance.get_parsed_data():
                    mac = data.get('mac')
                    ip = data.get('ip')
                    if mac and ip:
                        mac_ip_correlation[mac].add(ip)

                new_arp_data = list(
                    map(lambda x: dict([('mac', x[0]), ('related_ips', list(x[1]))]), mac_ip_correlation.items()))

                arp_instance.parsed_data = new_arp_data

                for arp_data in new_arp_data:
                    if len(arp_data['related_ips']) != 1:
                        continue

                    ip = arp_data['related_ips'][0]

                    sum_ = sum(map(lambda x: x.get_parsed_data(),
                                   filter(lambda x: not isinstance(x, ArpCiscoData),
                                          self._instances)), [])
                    if not ip in map(lambda x: x.get('ip'), sum_):
                        continue

                    # found colrreation
                    arp_data['ip'] = ip
                    del arp_data['related_ips']

                arp_instance.parsed_data = new_arp_data
            except Exception:
                logger.exception('Error while tring to correlate cdp')

        return itertools.chain.from_iterable(map(lambda x: x.get_devices(create_device_callback), self._instances))
