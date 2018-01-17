"""
symantec_adapter.py: An adapter for Tenable's Nessus Vulnerability scanning platform.
"""
__author__ = 'Shira Gold'

from axonius.adapter_base import AdapterBase
from axonius.adapter_exceptions import AdapterException, ClientConnectionException
from nessus_connection import NessusConnection
from nessus_exceptions import NessusException
from axonius.parsing_utils import figure_out_os
from axonius.consts.adapter_consts import SCANNER_FIELD

HOST = 'host'
PORT = 'port'
USERNAME = 'username'
PASSWORD = 'password'


class NessusAdapter(AdapterBase):
    def _get_client_id(self, client_config):
        """
        A unique value, from a predefined field, representing given client

        :param client_config: Object containing values for needed client credentials
        :return: str unique id for the client
        """
        return client_config[HOST]

    def _connect_client(self, client_config):
        """


        :param client_config:
        :return:
        """
        try:
            connection = NessusConnection(logger=self.logger, host=client_config[HOST],
                                          port=(client_config[PORT] if PORT in client_config else None))
            connection.set_credentials(username=client_config[USERNAME], password=client_config[PASSWORD])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except NessusException as e:
            port = client_config[PORT] if PORT in client_config else ''
            message = 'Error connecting to client with address {0} and port {1}, reason: {2}'.format(
                client_config[HOST], port, str(e))
            self.logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Use given connection to fetch all scans and for each scan, fetch all hosts.

        :param client_name: Unique name representing the client
        :param client_data: NessusConnection providing access to the client
        :return:
        """
        try:
            with client_data:
                device_dict = {}
                # Get all scans for client
                for scan in client_data.get_scans():
                    if scan.get('id') is None:
                        continue
                    # Get all hosts for scan
                    for host in client_data.get_hosts(scan['id']):
                        if host.get('host_id') is None or host.get('hostname') is None:
                            continue
                        # Get specific details of the host
                        host_details = client_data.get_host_details(scan['id'], host['host_id'])
                        if not host_details:
                            continue

                        hostname = host['hostname']
                        if hostname not in device_dict:
                            # Add host that is not yet listed in dict
                            host_details['id'] = hostname
                            host_details['scans'] = {}
                            device_dict[hostname] = host_details
                        # Add current scan info to the host, by scan id
                        device_dict[hostname]['scans'][scan['id']] = host

                return device_dict.values()
        except NessusException:
            self.logger.exception(f'Error querying devices from client {client_name}')
            raise AdapterException('Nessus Adapter failed querying devices for {0}'.format(client_name))

    def _clients_schema(self):
        """
        Definition of the credentials needed for connecting to a Nessus client.
        Once connection is established, use returned token in requests' HTTP header:
        X-Cookie: token={returned token}

        :return: JSON schema defining the credential properties
        """
        return {
            'properties': {
                HOST: {
                    'type': 'string',
                    'name': 'Host Address'
                },
                PORT: {
                    'type': 'number',
                    'name': 'Port'
                },
                USERNAME: {
                    'type': 'string',
                    'name': 'Username'
                },
                PASSWORD: {
                    'type': 'password',
                    'name': 'Password'
                }
            },
            'required': [HOST, USERNAME, PASSWORD],
            'type': 'object'
        }

    def _parse_raw_data(self, raw_data):
        """
        Generator creating parsed version of each device

        :param raw_data: Data as originally retrieved from Nessus
        :return: Data structured as expected by adapters
        """
        try:
            for device_raw in raw_data:
                yield {'id': device_raw['id'],
                       'hostname': '',
                       'OS': figure_out_os(device_raw.get('info', {}).get('operating-system', '')),
                       'network_interfaces': [
                           {'MAC': device_raw.get('info', {}).get('mac-address', ''),
                            'IP': device_raw.get('info', {}).get('host-ip', '')
                            }
                ],
                    SCANNER_FIELD: True,
                    'raw': device_raw}
        except NessusException as e:
            self.logger.exception('Error parsing devices.')
            raise AdapterException('Nessus Adapter failed parsing devices')
