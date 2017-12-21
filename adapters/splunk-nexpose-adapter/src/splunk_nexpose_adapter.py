"""
splunk_nexpose_adapter.py: An adapter for Splunk Dashboard.
"""
from configparser import ConfigParser

from axonius.AdapterExceptions import ClientConnectionException
from axonius.AdapterBase import AdapterBase
from axonius.ParsingUtils import figure_out_os
from splunk_connection import SplunkConnection

__author__ = "Asaf & Tal"


class SplunkNexposeAdapter(AdapterBase):

    def _get_client_id(self, client_config):
        return '{}:{}'.format(client_config['host'], client_config['port'])

    def _connect_client(self, client_config):
        try:
            connection = SplunkConnection(**client_config)
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as e:
            message = "Error connecting to client {0}, reason: {1}".format(self._get_client_id(client_config), str(e))
            self.logger.error(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Splunk domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Splunk connection

        :return: A json with all the attributes returned from the Splunk Server
        """
        with client_data:
            return list(client_data.get_nexpose_devices())

    def _clients_schema(self):
        """
        The schema SplunkNexposeAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "properties": {
                "host": {
                    "type": "string",
                    "name": "Host"
                },
                "port": {
                    "type": "integer",
                    "name": "Port"
                },
                "username": {
                    "type": "string",
                    "name": "Username"
                },
                "password": {
                    "type": "password",
                    "name": "Password"
                }
            },
            "required": [
                "host",
                "port",
                "username",
                "password"
            ],
            "type": "object"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device_parsed = dict()
            device_parsed['hostname'] = device_raw.get('hostname', None)
            device_parsed['OS'] = figure_out_os(device_raw.get('version', device_raw.get('os', None)))
            device_parsed['network_interfaces'] = [{'MAC': device_raw.get('mac', None),
                                                    'IP': device_raw.get('ip', None)}]
            device_parsed['id'] = device_raw['asset_id']
            device_parsed['raw'] = device_raw
            yield device_parsed
