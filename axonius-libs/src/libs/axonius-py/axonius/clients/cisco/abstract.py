import logging
logger = logging.getLogger(f"axonius.{__name__}")

from axonius.devices.device_adapter import DeviceAdapter, Field, ListField, format_ip, JsonStringFormat
import itertools

from collections import defaultdict


class CiscoDevice(DeviceAdapter):
    fetch_proto = Field(str, "Fetch Protocol", enum=['ARP', 'CDP', 'DHCP'])
    related_ips = ListField(str, 'Realated IPs', converter=format_ip, json_format=JsonStringFormat.ip,
                            description='A list of ips that routed through the device')
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

    def query_all(self):
        assert self._in_context

        for callback in [self.query_arp_table, self.query_dhcp_leases, self.query_cdp_table]:
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
        then in _parse_raw_data we can call create_device'''

    def __init__(self, raw_data):
        self._raw_data = raw_data
        self.parsed_data = None

    def _parse(self) -> dict:
        raise NotImplementedError()

    def get_parsed_data(self) -> dict:
        if not self.parsed_data:
            self.parsed_data = list(self._parse())
        return self.parsed_data

    def _get_devices(self, instance: dict, create_device_callback):
        if 'mac' not in instance:
            logger.warning(f'mac not found in instance {instance}')
            return None

        new_device = create_device_callback()

        new_device.id = instance['mac']
        ip = instance.get('ip')
        ips = [ip]
        if not ip:
            ips = []
        new_device.add_nic(instance['mac'], ips=ips)

        if 'related_ips' in instance:
            new_device.related_ips = instance['related_ips']

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


class ArpCiscoData(AbstractCiscoData):
    def __init__(self, raw_data):
        super().__init__(raw_data)

    def _get_devices(self, instance, create_device_callback):
        device = super()._get_devices(instance, create_device_callback)
        if device:
            device.fetch_proto = 'ARP'
            device.id = 'arp_' + device.id
        return device


class DhcpCiscoData(AbstractCiscoData):
    def __init__(self, raw_data):
        super().__init__(raw_data)

    def _get_devices(self, instance, create_device_callback):
        device = super()._get_devices(instance, create_device_callback)
        if device:
            device.fetch_proto = 'DHCP'
            device.id = 'dhcp_' + device.id
        return device


class CdpCiscoData(AbstractCiscoData):
    def __init__(self, raw_data):
        super().__init__(raw_data)

    def _get_devices(self, instance: dict, create_device_callback):
        if 'Device ID' not in instance:
            logger.warning(f'Device ID not found in instace {instance}')
            return None

        new_device = create_device_callback()

        # TODO: we must add the interface as part of the id so correlation will work
        new_device.id = instance['Device ID']
        new_device.id = 'cdp_' + new_device.id
        new_device.fetch_proto = 'CDP'

        if 'IP address' in instance:
            mac = instance.get('mac')
            new_device.add_nic(mac, ips=[instance['IP address']])

        new_device.hostname = instance.get('Device ID', '')
        new_device.device_model = instance.get('Platform', '')

        new_device.figure_os(instance.get('Platform', ''))
        new_device.os.build = instance.get('Version', '')

        new_device.set_raw(instance)
        return new_device


class InstanceParser(object):
    ''' parse multiple instances of CiscoData, correlate and return devices 
        This class exists because we need some way to correlate between arp table 
        and cdp table '''

    def __init__(self, instances):
        self._instances = list(instances)

    def get_devices(self, create_device_callback):
        cdp_instance = list(filter(lambda x: isinstance(x, CdpCiscoData), self._instances))
        arp_instance = list(filter(lambda x: isinstance(x, ArpCiscoData), self._instances))

        if cdp_instance:
            cdp_instance = cdp_instance[0]
        if arp_instance:
            arp_instance = arp_instance[0]

        # For each cdp device - check if we also see it in any other table (arp and dhcp) if we do - copy mac for correlation
        for cdp_data in cdp_instance.get_parsed_data():
            try:
                if cdp_data.get('mac'):
                    continue

                for other_data in sum(list(map(lambda x: x.get_parsed_data(), filter(lambda x: not isinstance(x, CdpCiscoData), self._instances))), []):
                    if cdp_data.get('IP address') == other_data.get('ip'):
                        cdp_data['mac'] = other_data.get('mac')
                        break
            except Exception:
                logger.exception('Error while tring to correlate cdp')

        try:
            mac_ip_correlation = defaultdict(set)
            for data in arp_instance.get_parsed_data():
                mac = data.get('mac')
                ip = data.get('ip') or data.get('IP address')
                if mac and ip:
                    mac_ip_correlation[mac].add(ip)

            new_arp_data = list(
                map(lambda x: dict([('mac', x[0]), ('related_ips', list(x[1]))]), mac_ip_correlation.items()))

            arp_instance.parsed_data = new_arp_data

            for arp_data in new_arp_data:
                if len(arp_data['related_ips']) != 1:
                    continue

                ip = arp_data['related_ips'][0]

                if not ip in map(lambda x: x.get('ip') or x.get('IP address'), sum(map(lambda x: x.get_parsed_data(), filter(lambda x: not isinstance(x, ArpCiscoData), self._instances)), [])):
                    continue

                # found colrreation
                arp_data['ip'] = ip
                del arp_data['related_ips']

            arp_instance.parsed_data = new_arp_data
        except Exception:
            logger.exception('Error while tring to correlate cdp')

        return itertools.chain.from_iterable(map(lambda x: x.get_devices(create_device_callback), self._instances))
