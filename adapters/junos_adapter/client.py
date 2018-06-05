''' client module for junos devices '''
import logging
from netmiko import ConnectHandler

logger = logging.getLogger(f"axonius.{__name__}")


class JunOSClient(object):
    ''' client to fetch data from junos devices '''

    def __init__(self, host, username, password, port):
        self._host = host
        self._username = username
        self._password = password
        self._port = port

        self._sess = None

    def __enter__(self):
        """ entry that connect to the juniper device. """
        self._sess = ConnectHandler(device_type='juniper_junos', ip=self._host,
                                    username=self._username, password=self._password, port=self._port)
        return self

    def __exit__(self, *args):
        """ exit function to close connection """
        self._sess.disconnect()

    def query_arp_table(self):
        """ query the arp table and return neighbors """
        # Strip and remove first and last line.

        data = self._sess.send_command('show arp')
        data = data.strip().splitlines()[1:]
        # If we have multiline result, remove the "Total entries" suffix
        if len(data) > 1:
            data = data[:-1]
        return data
