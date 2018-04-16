#!/usr/bin/env python3

import logging
logger = logging.getLogger(f"axonius.{__name__}")

from collections import defaultdict
import requests
from urllib.parse import urljoin
import socket
import struct
from axonius.utils.json import validate, JsonFieldError
from axonius.adapter_exceptions import ClientConnectionException


def cidr_to_netmask(cidr):
    """
    convert cidr (<ip>/<netmask> string) to ip, subnet
    :return: ip, subnet tuple
    """
    network, net_bits = cidr.split('/')
    host_bits = 32 - int(net_bits)
    netmask = socket.inet_ntoa(struct.pack('!I', (1 << 32) - (1 << host_bits)))
    return network, netmask


class CiscoPrimeException(Exception):
    pass


class CiscoPrimeClient:
    def __init__(self, url, username, password):
        self._url = url
        self._username = username
        self._password = password

        self._sess = None

    def get(self, path, *args, **kwargs):
        """
        Wrapper for invoking session get
        Disables ssl verify, adds url and creds.
        """
        url = urljoin(self._url, path)
        logger.debug(f'getting {url}')
        resp = self._sess.get(url, *args, **kwargs, verify=False, auth=(self._username, self._password))
        if resp.status_code != 200:
            raise CiscoPrimeExcpetion(f'Got unexpected status code {resp.status_code}')
        return resp

    def connect(self):
        """
        Open session using the given creds.
        Get data.json page to get cookie.
        """
        logger.info(f'Creating session using {self._username}')
        try:
            self._sess = requests.Session()
            resp = self.get('/webacs/api/v3/data.json')
        except CiscoPrimeException as e:
            raise ClientConnectionException(f'Invalid creds for api test')
        except Exception as e:
            raise ClientConnectionException(e)
        logger.debug(f'Connected to cisco prime {self._url}')

    def get_devices(self):
        """
        Get device list using Cisco Prime API.
        Requires active session.
        :return: json that contains a list of the devices
        """

        # number of devices per request we can play with this number for better preformence
        max_results = 100
        first_result = 0
        total_devices = 1

        # Check that self.connect() called
        if self._sess is None:
            raise CiscoPrimeException('Unable to get instace list without session')

        while first_result < total_devices:
            response = self.get(
                f'/webacs/api/v3/data/InventoryDetails.json?.full=true&.firstResult={first_result}&.maxResults={max_results}').json()
            response = response['queryResponse']

            # parse number of devices only if we in  the first response
            if first_result == 0:
                total_devices = int(response['@count'])
                logging.info(f"total number of devices = {total_devices}")

            first_result += len(response['entity'])

            # now fetch full info of the device and yield it
            for entity in response['entity']:
                device = entity.get('inventoryDetailsDTO', None)
                if device:
                    yield device

    @staticmethod
    def get_nics(device):
        """ 
        Extract mac, list((ip, subnet), ...) from device json
        :return: json that conatins the ifaces
        """

        # validate that the device has the nic structure, return empty list if it isn't
        try:
            validate({'ipInterfaces': {'ipInterface': ['ipAddress', 'name']}}, device)
            validate({'ethernetInterfaces': {'ethernetInterface': ['name', 'macAddress']}}, device)
        except JsonFieldError as e:
            logging.exception(f'invalid fields in device {device}')
            return {}

        ethernet_interfaces = device['ethernetInterfaces']['ethernetInterface']
        ip_interfaces = device['ipInterfaces']['ipInterface']

        # TODO: for now we only get interface that has ip
        # TODO: The algorithem complexity is O(nm) we can do much better by sorting creating dict of ether by name.
        result = defaultdict(list)
        for ipiface in ip_interfaces:
            for etheriface in ethernet_interfaces:
                if etheriface['name'] == ipiface['name']:
                    ip_subnet = (ipiface['ipAddress'], None)

                    # we got ip in cidr format (x.y.z.n/m)
                    if '/' in ip_subnet[0]:
                        ip_subnet = cidr_to_netmask(ip_subnet[0])

                    # ignore empty ip interfaces
                    if ip_subnet[0] == '0.0.0.0':
                        continue

                    result[(etheriface['name'], etheriface['macAddress'])].append(ip_subnet)
        return result
