import logging
logger = logging.getLogger(f"axonius.{__name__}")
import requests
from orionsdk import SwisClient


class SolarwindsConnection(object):
    def __init__(self, domain, username, password, verify_ssl):
        self.domain = domain
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl

    def connect(self):
        """
        IP must from the patrolling user
        :return: an instance if the Orion Swis client
        """
        if not self.verify_ssl:
            from requests.packages.urllib3.exceptions import InsecureRequestWarning
            requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

        # password can be none, username cannot
        try:
            swis = SwisClient(self.domain, self.username, self.password)
            self.client = swis
        except Exception as e:
            # whether username is none or is just incorrect, we need to raise an appropriate error
            raise ValueError(f"Error connecting to the server: {str(e)}")

    def get_device_list(self):
        """
        Makes an SQL query using the SwisClient API that obtains the following
        information about each node in the network.
        :return: raw list of all of the devices.
        """
        mac_address_q = self.client.query("SELECT NodeID, MAC FROM Orion.NodeMACAddresses")
        logger.info("Fetched mac address data")

        node_id_to_mac = {}
        for node in mac_address_q.get("results", []):
            node_id = node.get("NodeID", "")
            current_mac = node.get("MAC", "")

            if node_id and current_mac:
                if node_id not in node_id_to_mac:
                    node_id_to_mac[node_id] = []
                node_id_to_mac[node_id].append(current_mac)

        logger.info("Added mac address data to corresponding node")

        node_results = self.client.query("""SELECT NodeID, IPAddress, Location, CPUCount, IPAddressGUID, 
                                        NodeName, Uri, CPULoad, MemoryUsed, MemoryAvailable, PercentMemoryAvailable, 
                                        PercentMemoryUsed, IPAddressType, Caption, NodeDescription, Description, 
                                        SysObjectID FROM Orion.Nodes""")

        for node in node_results.get("results", []):
            try:
                node_id = node.get("NodeID", "")

                if node_id in node_id_to_mac:
                    node["MacAddresses"] = node_id_to_mac[node_id]
                yield node
            except Exception:
                logger.exception(f"Problem parsing specific node {node}")

        logger.info("Parsed all of the device data from the Orion DB")
