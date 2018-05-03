import logging
logger = logging.getLogger(f"axonius.{__name__}")


class AbstractCiscoClient:
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

    def query_arp_table(self):
        assert self._in_context
        return self._query_arp_table()


class AbstractCiscoData:
    '''Abstract class for cisco data. 
        each cisco client query should return CiscoData class, 
        that will be yielded in _query_device_by_client.
        then in _parse_raw_data we can call create_device'''

    def __init__(self, raw_data):
        self._raw_data = raw_data

    def parse(self):
        raise NotImplementedError()

    def _get_devices(self, instance, create_device_callback):
        if 'mac' not in instance:
            return None

        new_device = create_device_callback()

        new_device.id = instance['mac']
        if 'ip' in instance:
            new_device.add_nic(instance['mac'], ips=[instance['ip']])

        return new_device

    def get_devices(self, create_device_callback):
        for instance in self.parse():
            # without mac we can not create device
            try:
                new_device = self._get_devices(instance, create_device_callback)
                if new_device:
                    yield new_device
            except:
                logger.exception('Exception while getting devices')


class ArpCiscoData(AbstractCiscoData):
    def __init__(self, raw_data):
        super().__init__(raw_data)

    def parse(self):
        raise NotImplementedError()

    def _get_devices(self, instance, create_device_callback):
        device = super()._get_devices(instance, create_device_callback)
        if device:
            device.device_model = 'cisco neighbor'
        return device
