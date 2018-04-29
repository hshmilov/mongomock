#!/usr/bin/env python3

import logging
logger = logging.getLogger(f"axonius.{__name__}")

from collections import defaultdict
import requests
from urllib.parse import urljoin
import socket
import struct
from axonius.utils import json
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
            raise CiscoPrimeException(f'Got unexpected status code {resp.status_code}')
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

    def _get_devices(self, first_result=0, max_results=100):
        try:
            response = self.get(
                f'/webacs/api/v3/data/InventoryDetails.json?.full=true&.firstResult={first_result}&.maxResults={max_results}').json()
        except Exception as e:
            logger.exception(f'Got exception while getting devices {first_result} {max_results}')
            return {}

        if not json.is_valid(response, {'queryResponse': '@count'},
                             {'queryResponse': 'entity'}):
            logger.warning(f'Got invalid json {response}')
            return {}

        return response

    def get_devices(self):
        """
        Get device list using Cisco Prime API.
        Requires active session.
        :return: json that contains a list of the devices
        """

        first_result = 0
        total_devices = 1
        number_of_failed_response = 0

        # Check that self.connect() called
        if self._sess is None:
            raise CiscoPrimeException('Unable to get instace list without session')

        while first_result < total_devices:
            response = self._get_devices(first_result)
            if not response:
                logger.warning(f'Skipping empty result {first_result}')

                if number_of_failed_response > 3:
                    logger.error('Failed more then 3 times to get devices from server - giving up')
                    break

                number_of_failed_response += 1
                continue

            response = response['queryResponse']

            # Parse number of devices only if we in  the first response
            if first_result == 0:
                total_devices = int(response['@count'])
                logger.info(f"total number of devices = {total_devices}")

            if len(response['entity']) == 0:
                logger.error('Got empty entity list - giving up')
                break

            first_result += len(response['entity'])

            # Now fetch full info of the device and yield it
            for entity in response['entity']:
                # validate that the device contains inventory
                device = entity.get('inventoryDetailsDTO', '')
                if device:
                    yield device

    @staticmethod
    def get_nics(device):
        """ 
        Extract mac, list((ip, subnet), ...) from device json
        :return: json that conatins the ifaces
        """

        # validate that the device has the nic structure, return empty list if it isn't
        if not json.is_valid(device,
                             {'ipInterfaces': {'ipInterface': ['ipAddress', 'name']}},
                             {'ethernetInterfaces': {'ethernetInterface': ['name', 'macAddress']}}):
            logger.warning(f'Invalid nics for device {device}')
            return {}

        ethernet_interfaces = device['ethernetInterfaces']['ethernetInterface']
        ip_interfaces = device['ipInterfaces']['ipInterface']

        # TODO: for now we only get interface that has ip
        # TODO: The algorithem complexity is O(nm) we can do much better by sorting creating dict of ether by name.
        try:
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
        except Exception as e:
            logger.exception(f'Unable to parse nics for device {device}')
            return {}
        return result

    def _get_credentials(self, device):
        """ 
        request (snmp, ssh, etc) creds for given device
        :return: json that conatins creds
        """
        if not json.is_valid(device, '@id'):
            logger.warning('device is missing @id')
            return {}

        id_ = device['@id']

        try:
            resp = self.get(f'/webacs/api/v1/op/cm/credentials.json?id={id_}')
            resp = resp.json()
        except Exception as e:
            logger.exception(f'Got exception while getting creds {creds}')
            return {}

        return resp

    def get_credentials(self, device):
        """
        get raw json using _get_credential and convert it to name, value dict
        :return: json that contains name, value
        """

        creds = self._get_credentials(device)
        if creds == {}:
            return {}

        if not json.is_valid(creds, {'mgmtResponse': {'credentialDTO': {'credentialList': {'credentialList': ['propertyName', 'stringValue']}}}}):
            logger.warning(f'Got invalid cred {creds} json for device {device}')
            return {}

        # Convert to one dict
        creds = dict(map(lambda cred: (cred['propertyName'], cred['stringValue']),
                         creds['mgmtResponse']['credentialDTO']['credentialList']['credentialList']))
        return creds
