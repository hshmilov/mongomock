#!/usr/bin/env python3

import logging
import socket
import struct
from collections import defaultdict
from urllib.parse import urljoin

import requests

from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils import json

logger = logging.getLogger(f'axonius.{__name__}')


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
            raise ClientConnectionException(str(e))
        logger.debug(f'Connected to cisco prime {self._url}')

    def disconnect(self):
        self._sess.close()
        self._sess = None

    def _get_devices(self, first_result=0, max_results=100):
        try:
            response = self.get(
                f'/webacs/api/v3/data/InventoryDetails.json'
                f'?.full=true&.firstResult={first_result}&.maxResults={max_results}').json()
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
                logger.info(f'total number of devices = {total_devices}')

            if not response['entity']:
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

        # XXX: for now we only get interface that has ip
        # XXX: The algorithem complexity is O(nm) we can do much better by sorting creating dict of ether by name.
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
            logger.exception(f'Got exception while getting creds {id_}')
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

        validator = \
            {'mgmtResponse': {'credentialDTO': {'credentialList': {'credentialList': ['propertyName', 'stringValue']}}}}
        if not json.is_valid(creds, validator):
            logger.warning(f'Got invalid cred {creds} json for device {device}')
            return {}

        # Convert to one dict
        creds = dict(map(lambda cred: (cred['propertyName'], cred['stringValue']),
                         creds['mgmtResponse']['credentialDTO']['credentialList']['credentialList']))
        return creds



# Simple tests
if __name__ == '__main__':
    def main():
        from axonius.clients.cisco import snmp
        from pprint import pprint
        from test_credentials.test_cisco_prime_credentials import client_details

        logging.basicConfig(level=logging.DEBUG)
        client = CiscoPrimeClient(**client_details)
        client.connect()

        devices = list(client.get_devices())
        for device in devices:
            # pprint(device)
            # pprint(client.get_nics(device))
            # for mac, iplist in client.get_nics(device).items():
            #    print(f'{mac}: {list(map(lambda x: x[0], iplist))}')
            # pprint(client.get_credentials(device))
            pass
        creds = client.get_credentials(devices[2])
        if creds:
            pprint(creds)
            a = snmp.CiscoSnmpClient(creds['snmp_read_cs'], creds['MANAGEMENT_ADDRESS'], creds['snmp_port'])
            pprint(list(a.query_arp_table()))
    main()
