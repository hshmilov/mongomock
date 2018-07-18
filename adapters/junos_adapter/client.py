''' client module for junos devices '''
import logging
from jnpr.junos import Device
from jnpr.junos.op.arp import ArpTable
import json

logger = logging.getLogger(f"axonius.{__name__}")


class JunOSClient(object):
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
        arp_table = ArpTable(self._dev)
        raw_table_data = list(arp_table.get())
        return raw_table_data
