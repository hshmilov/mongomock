"""
splunk_symantec_adapter.py: An adapter for Splunk Dashboard.
"""

from axonius.adapter_exceptions import ClientConnectionException
from axonius.adapter_base import AdapterBase
from axonius.device import Device, IPS_FIELD, MAC_FIELD
from splunk_connection import SplunkConnection

__author__ = "Asaf & Tal"

SPLUNK_HOST = 'host'
SPLUNK_PORT = 'port'
SPLUNK_USER = 'username'
SPLUNK_PASSWORD = 'password'
SPLUNK_ONLINE_HOURS = 'online_hours'


class SplunkSymantecAdapter(AdapterBase):

    class MyDevice(Device):
        pass

    def __init__(self, **kwargs):
        # Initialize the base plugin (will initialize http server)
        super().__init__(**kwargs)
        self._online_hours = 24

    def _get_client_id(self, client_config):
        return '{0}:{1}'.format(client_config[SPLUNK_HOST], client_config[SPLUNK_PORT])

    def _connect_client(self, client_config):
        try:
            self._online_hours = int(client_config[SPLUNK_ONLINE_HOURS] or self._online_hours)
            assert self._online_hours > 0, "You entered an invalid amount of hours as online hours"
            # copying as otherwise we would pop it from the client saved in the gui
            client_con = client_config.copy()
            client_con.pop(SPLUNK_ONLINE_HOURS)
            connection = SplunkConnection(**client_con)
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as e:
            message = "Error connecting to client {0}, reason: {1}".format(self._get_client_id(client_config), str(e))
            self.logger.exception(message)
            raise ClientConnectionException(message)

    def get_last_query_ts(self, name):
        ts_collection = self._get_collection('queries_ts', limited_user=True)
        for item in ts_collection.find({'query_name': name}):
            return item['ts']
        return None

    def set_last_query_ts(self, name, ts):
        ts_collection = self._get_collection('queries_ts', limited_user=True)
        ts_collection.update({'query_name': name}, {'query_name': name, 'ts': ts}, upsert=True)

    def _update_new_raw_devices(self, client_data, queries_collection):
        already_updates = []
        last_ts = self.get_last_query_ts('symantec')
        for host in client_data.get_symantec_devices_info(last_ts):
            name = host['name']
            if name in already_updates:
                continue
            already_updates.append(name)
            queries_collection.update({'name': name}, {'name': name, 'host': host}, upsert=True)
            timestamp = client_data.parse_time(host['timestamp'])
            if last_ts is None or last_ts < timestamp:
                last_ts = timestamp
        if last_ts is not None:
            self.set_last_query_ts('symantec', int(last_ts + 1))

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Splunk domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Splunk connection

        :return: A json with all the attributes returned from the Splunk Server
        """
        with client_data:
            queries_collection = self._get_collection('symantec_queries', limited_user=True)
            # Update all_devices from splunk
            self._update_new_raw_devices(client_data, queries_collection)

            # Get "Active" devices
            active_hosts = client_data.get_symantec_active_hosts(self._online_hours)

            #
            if active_hosts:
                all_devices = list(queries_collection.find({'$or': [{'name': name} for name in active_hosts]}))
            else:
                all_devices = []
            return all_devices

    def _clients_schema(self):
        """
        The schema SplunkSymantecAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "properties": {
                SPLUNK_HOST: {
                    "type": "string",
                    "name": "Host"
                },
                SPLUNK_PORT: {
                    "type": "integer",
                    "name": "Port"
                },
                SPLUNK_USER: {
                    "type": "string",
                    "name": "Username"
                },
                SPLUNK_PASSWORD: {
                    "type": "password",
                    "name": "Password"
                },
                SPLUNK_ONLINE_HOURS: {
                    "type": "integer",
                    "name": "Hours within device is considered online (default is 24)"
                }
            },
            "required": [
                SPLUNK_HOST,
                SPLUNK_PORT,
                SPLUNK_USER,
                SPLUNK_PASSWORD
            ],
            "type": "object"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            host = device_raw.get('host', '')
            device = self._new_device()
            device.hostname = host.get('name', '')
            if host.get('type', '') == 'symantec_mac':
                device.figure_os('OS X')
                if host.get('local mac', '') != '000000000000':
                    device.add_nic(':'.join([host.get('local mac', '')[index:index + 2] for index in range(0, 12, 2)]),
                                   host.get('local ips', '').split(' '))
                if host.get('remote mac', '') != '000000000000':
                    device.add_nic(':'.join([host.get('remote mac', '')[index:index + 2] for index in range(0, 12, 2)]),
                                   host['remote ips'].split(' '))
            else:
                device.figure_os(host.get('os', ''))
                for iface in host.get('network', []):
                    device.add_nic(iface.get(MAC_FIELD, ''), iface.get(IPS_FIELD, '').split(' '))
            device.id = host['name']
            device.set_raw(device_raw)
            yield device
