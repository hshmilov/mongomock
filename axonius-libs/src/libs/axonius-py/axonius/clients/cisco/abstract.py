import logging
logger = logging.getLogger(f"axonius.{__name__}")

from axonius.devices.device_adapter import DeviceAdapter, Field, ListField, format_ip, JsonStringFormat


class CiscoDevice(DeviceAdapter):
    fetch_proto = Field(str, "Fetch Protocol", enum=['ARP', 'CDP', 'DHCP'])
    related_ips = ListField(str, 'IPs', converter=format_ip, json_format=JsonStringFormat.ip,
                            description='A list of ips that routed through the device')
    reachability = Field(str, "reachability")


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
        try:
            yield from self.query_arp_table()
        except Exception:
            logger.exception('Exception while querying arp')
        try:
            yield from self.query_dhcp_leases()
        except Exception:
            logger.exception('Exception while querying dhcp')
        try:
            yield from self.query_cdp_table()
        except Exception:
            logger.exception('Exception while querying cdp')


class AbstractCiscoData(object):
    '''Abstract class for cisco data. 
        each cisco client query should return CiscoData class, 
        that will be yielded in _query_device_by_client.
        then in _parse_raw_data we can call create_device'''

    def __init__(self, raw_data):
        self._raw_data = raw_data

    def parse(self) -> dict:
        raise NotImplementedError()

    def _get_devices(self, instance: dict, create_device_callback):
        if 'mac' not in instance:
            logger.warning(f'mac not found in instance {instance}')
            return None

        new_device = create_device_callback()

        new_device.id = instance['mac']
        if 'ip' in instance:
            new_device.add_nic(instance['mac'], ips=[instance['ip']])

        # TODO: the real raw data is self._raw_data
        # but it isn't a dict so for now we only save the instance - which must be a dict
        new_device.set_raw(instance)
        return new_device

    def get_devices(self, create_device_callback):
        for instance in self.parse():
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
        logger.info(f'instance = {instance}')
        new_device = create_device_callback()

        new_device.id = instance['Device ID']
        new_device.fetch_proto = 'CDP'

        if 'IP address' in instance:
            new_device.add_nic(ips=[instance['IP address']])

        new_device.hostname = instance.get('Device ID', '')
        new_device.device_model = instance.get('Platform', '')

        new_device.id = 'cdp_' + new_device.id
        new_device.figure_os('cisco')
        new_device.os.build = instance.get('Version', '')

        new_device.set_raw(instance)
        return new_device


class InstanceParser(object):
    ''' parse multiple instances of CiscoData, correlate and return devices 
        This class exists because we need some way to correlate between arp table 
        and cdp table '''

    def __init__(self, instances):
        self._instances = instances

    def get_devices(self, create_device_callback):
        devices = set(sum(map(lambda i: list(i.get_devices(create_device_callback)), self._instances), []))
        cdp_devices = set(filter(lambda device: device.id.startswith('cdp'), devices))
        other_devices = devices - cdp_devices

        # correlate cdp
        for cdp_device in cdp_devices:
            for other_device in other_devices:
                for nic in other_device.network_interfaces:
                    if cdp_device.network_interfaces:
                        cdp_ips = cdp_device.network_interfaces[0].ips
                        if cdp_ips is not None and cdp_ips[0] in nic.ips:
                            # correlate
                            cdp_device.network_interfaces[0].mac = nic.mac
        return list(devices)
