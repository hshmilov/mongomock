""" client module for junos devices """
import logging


from ncclient.operations.rpc import RPCError
from jnpr.junos.exception import RpcError
from jnpr.junos import Device

logger = logging.getLogger(f'axonius.{__name__}')


class JunOSClient:
    """ client to fetch data from junos devices """

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

    def query_lldp_neighbors(self):
        """ query lldp neighbors and return data """
        return self._dev.rpc.get_lldp_neighbors_information()

    def query_basic_info(self):
        """ query the basic info xmls and return data """
        results = []
        for name, action in [
                ('interface list', self._dev.rpc.get_interface_information),
                ('hardware', self._dev.rpc.get_chassis_inventory),
                ('version', self._dev.rpc.get_software_information),
                ('vlans', lambda: self._dev.rpc.get_ethernet_switching_interface_information(detail=True)),
                ('base-mac', lambda: self._dev.rpc.get_chassis_mac_addresses),
        ]:
            try:
                results.append((name, action()))
            except (RPCError, RpcError) as e:
                logger.error(f'Failed to execute RPC Command: {str(e)}')
            except Exception:
                logger.exception('Failed to execute query')
        return results
