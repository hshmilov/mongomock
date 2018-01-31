"""
splunk_nexpose_adapter.py: An adapter for Splunk Dashboard.
"""
from configparser import ConfigParser

from axonius.adapter_exceptions import ClientConnectionException
from axonius.adapter_base import AdapterBase
from axonius.device import Device
from splunk_connection import SplunkConnection

__author__ = "Asaf & Tal"


class SplunkNexposeAdapter(AdapterBase):

    class MyDevice(Device):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config = ConfigParser()
        config.read(self.config_file_path)
        self.max_log_history = int(config['DEFAULT']['max_log_history'])  # in days

    def _get_client_id(self, client_config):
        return '{}:{}'.format(client_config['host'], client_config['port'])

    def _connect_client(self, client_config):
        try:
            connection = SplunkConnection(self.logger, **client_config)
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as e:
            message = "Error connecting to client {0}, reason: {1}".format(self._get_client_id(client_config), str(e))
            self.logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Splunk domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Splunk connection

        :return: A json with all the attributes returned from the Splunk Server
        """
        with client_data:
            return list(client_data.get_nexpose_devices(f'-{self.max_log_history}d'))

    def _clients_schema(self):
        """
        The schema SplunkNexposeAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "host",
                    "title": "Host Name",
                    "type": "string"
                },
                {
                    "name": "port",
                    "title": "Port",
                    "type": "number"
                },
                {
                    "name": "username",
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": "password",
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                }
            ],
            "required": [
                "host",
                "port",
                "username",
                "password"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._new_device()
            device.hostname = device_raw.get('hostname', '')
            device.figure_os(device_raw.get('version', device_raw.get('os')))
            device.add_nic(device_raw.get('mac'), [device_raw.get('ip')], self.logger)
            device.id = device_raw['asset_id']
            device.scanner = True
            device.set_raw(device_raw)
            yield device
