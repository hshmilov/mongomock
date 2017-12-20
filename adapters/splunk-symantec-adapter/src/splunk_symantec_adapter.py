"""
splunk_symantec_adapter.py: An adapter for Splunk Dashboard.
"""
from configparser import ConfigParser

from axonius.AdapterExceptions import ClientConnectionException
from axonius.AdapterBase import AdapterBase
from axonius.ParsingUtils import figure_out_os
from splunk_connection import SplunkConnection

__author__ = "Asaf & Tal"


class SplunkSymantecAdapter(AdapterBase):

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
        config = ConfigParser()
        config.read(self.config_file_path)

        host_active_hours = int(config['DEFAULT']['host_active_hours'])
        with client_data:
            queries_collection = self._get_collection('symantec_queries', limited_user=True)
            self._update_new_raw_devices(client_data, queries_collection)
            active_hosts = client_data.get_symantec_active_hosts(host_active_hours)
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
            host = device_raw['host']
            device_parsed = dict()
            device_parsed['hostname'] = host['name']
            if host['type'] == 'symantec_mac':
                device_parsed['OS'] = figure_out_os('OS X')
                device_parsed['network_interfaces'] = []
                if host['local mac'] != '000000000000':
                    device_parsed['network_interfaces'].append({'MAC': host['local mac'],
                                                                'IP': host['local ips'].split(' ')})
                if host['remote mac'] != '000000000000':
                    device_parsed['network_interfaces'].append({'MAC': ':'.join([host['remote mac'][index:index + 2]
                                                                                 for index in range(0, 12, 2)]),
                                                                'IP': host['remote ips'].split(' ')})
            else:
                device_parsed['OS'] = figure_out_os(host['os'])
                device_parsed['network_interfaces'] = [{'MAC': iface['mac'],
                                                        'IP': iface['ip'].split(' ')} for iface in host['network']]
            device_parsed['id'] = host['name']
            device_parsed['raw'] = device_raw
            yield device_parsed
