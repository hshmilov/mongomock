''' client module for junos devices '''
from jnpr.junos import Device


class JunOSClient:
    ''' client to fetch data from junos devices '''

    def __init__(self, host, username, password, port):
        self._host = host
        self._username = username
        self._password = password
        self._port = port

        self._dev = None

    def __enter__(self):
        """ entry that connect to the juniper device. """
        self._dev = Device(host=self._host, user=self._username, password=self._password, port=self._port)
        self._dev.open()
        return self

    def __exit__(self, *args):
        """ exit function to close connection """
        self._dev.close()

    def query_arp_table(self):
        """ query the arp table and return neighbors """
        return self._dev.rpc.get_arp_table_information()

    def query_fdb_table(self):
        """ query the fdb table and return data """
        return self._dev.rpc.get_ethernet_switching_table_information()
