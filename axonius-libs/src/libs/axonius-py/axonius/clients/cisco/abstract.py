import logging
logger = logging.getLogger(f"axonius.{__name__}")

from axonius.devices.device_adapter import DeviceAdapter, Field, ListField, format_ip, JsonStringFormat
import itertools

from collections import defaultdict


class CiscoDevice(DeviceAdapter):
    # Fetch protocol refers to the way we discover new devices (by querying arp, cdp, dhcp tables, or by adding the client itself).
    fetch_proto = Field(str, "Fetch Protocol", enum=['ARP', 'CDP', 'DHCP', 'CLIENT'])
    reachability = Field(str, "Reachability")


class AbstractCiscoClient(object):
    ''' Abstract class for cisco's clients. 
        each function must raise ClientConnectionException for creds errors '''

    def __init__(self):
        self._in_context = False

    def __enter__(self):
        ''' entry that connect to the cisco device. '''
        self._in_context = True
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        ''' exit that to the cisco device. '''
        self._in_context = False

    def _query_arp_table(self):
        ''' This function should be overwritten by heir.'''
        raise NotImplementedError()

    def _query_dhcp_leases(self):
        ''' This function should be overwritten by heir.'''
        raise NotImplementedError()

    def _query_cdp_table(self):
        ''' This function should be overwritten by heir.'''
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


class AbstractCiscoData(object):
    '''Abstract class for cisco data. 
        each cisco client query should return CiscoData class, 
        that will be yielded in _query_device_by_client.
        then in _parse_raw_data we can call get_devices '''

    def __init__(self, raw_data):
        self._raw_data = raw_data
        self.parsed_data = None

    def _parse(self) -> dict:
        raise NotImplementedError()

    def get_parsed_data(self) -> dict:
        if not self.parsed_data:
            self.parsed_data = list(self._parse())
        return self.parsed_data

    def _get_id(self, instance):
        return instance.get('mac')

    def _get_devices(self, instance: dict, create_device_callback):
        """ This function gets instances (dicts that hold the "raw data") from _parse implemenataion of each CiscoData class
            and convert them to axonius devices.
            Each instance might hold different fields, so we assume that some or all fields might be missing.
            This function defines the instance structure.
        """

        id_ = self._get_id(instance)
        if id_ is None:
            logger.warning(f'Unable to create id_ for instace {instance}')
            return None

        new_device = create_device_callback()

        new_device.id = id_

        # TODO: we don't need ifaces and iface, there is duplication in the structure
        if any(['ip' in instance, 'mac' in instance, 'iface' in instance]):
            ips = [instance.get('ip')] if instance.get('ip') else []
            new_device.add_nic(mac=instance.get('mac'), name=instance.get('iface'), ips=ips)

        if 'ifaces' in instance:
            # TODO: add mtu, speed, state and etc to add_nic
            # TODO: validate that the length of ip list is equal to net-mask
            for iface in instance['ifaces'].values():
                ip_list = []
                netmask_list = []

                if 'ips' in iface:
                    ip_list = list(filter(bool, map(lambda x: x.get('address'), iface['ips'])))
                    netmask_list = filter(bool, map(lambda x: x.get('net-mask'), iface['ips']))
                    netmask_list = list(map(lambda x: '/'.join(x), zip(ip_list, netmask_list)))

                new_device.add_nic(mac=iface.get('mac'), name=iface.get(
                    'descritption'), ips=ip_list, subnets=netmask_list)

        new_device.hostname = instance.get('hostname')
        new_device.device_model = instance.get('device_model')

        new_device.figure_os(instance.get('device_model'))
        new_device.os.build = instance.get('version')

        if 'related_ips' in instance:
            new_device.add_related_ips(instance['related_ips'])

        # TODO: the real raw data is self._raw_data
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


class BasicInfoData(AbstractCiscoData):
    def _get_id(self, instance):
        id_ = '_'.join(['basic_info', instance.get('hostname', '')])
        if id_ == "basic_info":
            return None
        return id_

    def _get_devices(self, instance, create_device_callback):
        device = super()._get_devices(instance, create_device_callback)
        if device:
            device.fetch_proto = 'CLIENT'
        return device


class ArpCiscoData(AbstractCiscoData):
    def __init__(self, raw_data):
        super().__init__(raw_data)

    def _get_id(self, instance):
        return 'arp_' + instance.get('mac') if instance.get('mac') else None

    def _get_devices(self, instance, create_device_callback):
        device = super()._get_devices(instance, create_device_callback)
        if device:
            device.fetch_proto = 'ARP'
        return device


class DhcpCiscoData(AbstractCiscoData):
    def __init__(self, raw_data):
        super().__init__(raw_data)

    def _get_id(self, instance):
        mac = instance.get('mac')
        iface = instance.get('iface')
        id_ = 'dhcp'

        if not mac:
            return

        id_ += '_' + mac

        if iface:
            id_ += '_' + iface

        return id_

    def _get_devices(self, instance, create_device_callback):
        device = super()._get_devices(instance, create_device_callback)
        if device:
            device.fetch_proto = 'DHCP'
        return device


class CdpCiscoData(AbstractCiscoData):
    def __init__(self, raw_data):
        super().__init__(raw_data)

    def _get_id(self, instance):
        mac = instance.get('mac')
        iface = instance.get('iface')
        id_ = 'cdp'

        if not mac:
            return

        id_ += '_' + mac

        if iface:
            id_ += '_' + iface

        return id_

    def _get_devices(self, instance, create_device_callback):
        device = super()._get_devices(instance, create_device_callback)
        if device:
            device.fetch_proto = 'CDP'
        return device


class InstanceParser(object):
    ''' parse multiple instances of CiscoData, correlate and return devices 
        This class exists because we need some way to correlate between arp table 
        and cdp table '''

    def __init__(self, instances):
        self._instances = list(filter(lambda x: x is not None, instances))

    def get_devices(self, create_device_callback):
        cdp_instance = list(filter(lambda x: isinstance(x, CdpCiscoData), self._instances))
        arp_instance = list(filter(lambda x: isinstance(x, ArpCiscoData), self._instances))

        # For each cdp device - check if we also see it in any other table (arp and dhcp) if we do - copy mac for correlation
        if cdp_instance:
            cdp_instance = cdp_instance[0]

            # TODO: arp throws iface
            # TODO: cdp neighbors doesn't correlate when one have empty ip
            for cdp_data in cdp_instance.get_parsed_data():
                try:
                    if cdp_data.get('mac'):
                        continue

                    for other_data in sum(list(map(lambda x: x.get_parsed_data(), filter(lambda x: not isinstance(x, CdpCiscoData), self._instances))), []):
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

                    if not ip in map(lambda x: x.get('ip'), sum(map(lambda x: x.get_parsed_data(), filter(lambda x: not isinstance(x, ArpCiscoData), self._instances)), [])):
                        continue

                    # found colrreation
                    arp_data['ip'] = ip
                    del arp_data['related_ips']

                arp_instance.parsed_data = new_arp_data
            except Exception:
                logger.exception('Error while tring to correlate cdp')

        return itertools.chain.from_iterable(map(lambda x: x.get_devices(create_device_callback), self._instances))
