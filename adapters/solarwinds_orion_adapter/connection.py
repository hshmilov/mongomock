import logging
from urllib3.util.url import parse_url


import requests
from orionsdk import SwisClient

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=too-many-branches,too-many-statements,invalid-triple-quote


class SolarwindsConnection:
    def __init__(self, domain, username, password, verify_ssl):
        self.domain = parse_url(domain).host
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl

    def connect(self):
        """
        IP must from the patrolling user
        :return: an instance if the Orion Swis client
        """
        if not self.verify_ssl:
            # pylint: disable=import-error
            from requests.packages.urllib3.exceptions import InsecureRequestWarning
            # pylint: enable=import-error
            requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

        # password can be none, username cannot
        try:
            swis = SwisClient(self.domain, self.username, self.password)
            self.client = swis
            swis.query('SELECT Uri FROM Orion.Nodes WHERE NodeID=@id', id=1)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                raise ValueError(f'Error fetching devices: {str(e)}')
            raise ValueError(f'Error connecting to the server: {str(e)}')
        except Exception as e:
            raise ValueError(f'Error connecting to the server: {str(e)}')

    # pylint: disable=too-many-locals, too-many-branches, too-many-statements
    def get_device_list(self, fetch_ipam=True, custom_properties_list=None):
        """
        Makes an SQL query using the SwisClient API that obtains the following
        information about each node in the network.
        :return: raw list of all of the devices.
        """
        logger.info('Fetched mac address data')
        node_id_to_mac = {}
        try:
            mac_address_q = self.client.query('SELECT NodeID, MAC FROM Orion.NodeMACAddresses')
            for node in mac_address_q.get('results') or []:
                node_id = node.get('NodeID')
                current_mac = node.get('MAC')

                if node_id and current_mac:
                    if node_id not in node_id_to_mac:
                        node_id_to_mac[node_id] = []
                    node_id_to_mac[node_id].append(current_mac)
        except Exception:
            logger.exception(f'Problem getting MACs')
        logger.info('Fetching Custom properties')
        node_id_to_custom = {}
        try:
            if custom_properties_list:
                custom_properties_split = custom_properties_list.split(',')
                custom_properties_list = [prop.strip() for prop in custom_properties_split]
                if 'NodeID' not in custom_properties_list:
                    custom_properties_list.append('NodeID')
                custom_properties_list_final = ', '.join(custom_properties_list)
                custom_q = self.client.query(f'SELECT {custom_properties_list_final} FROM Orion.NodesCustomProperties')
                for node in custom_q.get('results') or []:
                    node_id = node.get('NodeID')
                    if node_id:
                        if node_id not in node_id_to_custom:
                            node_id_to_custom[node_id] = []
                        node_id_to_custom[node_id].append(node)
        except Exception:
            logger.exception(f'Problem getting custom properties')

        node_id_to_sw = {}
        try:
            sw_address_q = self.client.query(
                'SELECT NodeID, Name, Version, Publisher FROM Orion.AssetInventory.Software')
            for node in sw_address_q.get('results') or []:
                node_id = node.get('NodeID')
                current_name = node.get('Name')
                current_version = node.get('Version')
                current_publisher = node.get('Publisher')

                if node_id and current_name:
                    if node_id not in node_id_to_sw:
                        node_id_to_sw[node_id] = []
                    node_id_to_sw[node_id].append([current_name, current_version, current_publisher])
        except Exception:
            logger.exception(f'Problem getting SW')

        logger.info('Added mac address data to corresponding node')

        try:
            node_results = self.client.query("""SELECT NodeID, IPAddress, Location, CPUCount, IPAddressGUID, Vendor,
                                            NodeName, Uri, CPULoad, MemoryUsed, MemoryAvailable, PercentMemoryAvailable, 
                                            PercentMemoryUsed, IPAddressType, Caption, NodeDescription, Description, 
                                            SysObjectID FROM Orion.Nodes""")
        except Exception:
            node_results = self.client.query("""SELECT NodeID, IPAddress, Location, IPAddressGUID,
                                            NodeName, Uri, CPULoad, MemoryUsed, MemoryAvailable, PercentMemoryAvailable, 
                                            PercentMemoryUsed, IPAddressType, Caption, NodeDescription, Description, 
                                            SysObjectID FROM Orion.Nodes""")

        for node in node_results.get('results') or []:
            try:
                node_id = node.get('NodeID')

                if node_id in node_id_to_mac:
                    node['MacAddresses'] = node_id_to_mac[node_id]
                if node_id in node_id_to_sw:
                    node['sw_list'] = node_id_to_sw[node_id]
                if node_id in node_id_to_custom:
                    node['custom_properties'] = node_id_to_custom[node_id]
                yield node, 'node'
            except Exception:
                logger.exception(f'Problem parsing specific node {node}')
        try:
            wifi_results = self.client.query('Select  Description, Name, NodeID, LastUpdate, FirstUpdate,'
                                             ' MAC, IPAddress, ID, InstanceType, '
                                             'DisplayName, SSID from Orion.Packages.Wireless.Clients')
            if wifi_results and wifi_results.get('results'):
                for device_raw in wifi_results.get('results'):
                    yield device_raw, 'wifi'
        except Exception:
            logger.exception(f'Problem getting wifi info')
        try:
            lan_results = self.client.query('Select ConnectedTo, ConnectionTypeName, HostName, IPAddress,'
                                            ' MACAddress, PortNumber, PortName, '
                                            'NodeID, VLAN, DisplayName, Description from Orion.UDT.AllEndpoints')
            if lan_results and lan_results.get('results'):
                for device_raw in lan_results.get('results'):
                    yield device_raw, 'lan'
        except Exception:
            logger.exception(f'Problem getting lan info')
        try:
            if fetch_ipam:
                dhcp_results = self.client.query('Select IPAddress, MAC, LeaseExpires, '
                                                 'DhcpClientName, Vendor, MachineType, '
                                                 'Description, DisplayName, Status  from IPAM.IPNode')
                if dhcp_results and dhcp_results.get('results'):
                    for device_raw in dhcp_results.get('results'):
                        yield device_raw, 'dhcp'
        except Exception:
            logger.exception(f'Problem getting dhcp info')
        logger.info('Parsed all of the device data from the Orion DB')
