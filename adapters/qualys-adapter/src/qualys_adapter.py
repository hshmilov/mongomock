"""
QualysAdapter.py: An adapter for Qualys Dashboard.
"""

__author__ = "Asaf & Tal"

import axonius.adapter_exceptions
from axonius.adapter_base import AdapterBase
from axonius.parsing_utils import figure_out_os
import qualys_connection
import qualys_exceptions
from itertools import groupby

QUALYS_ITERATOR_FORMAT = """
<?xml version="1.0" encoding="UTF-8" ?>
<ServiceRequest>
 <preferences>
 <startFromId>{0}</startFromId>
 <limitResults>{1}</limitResults>
 </preferences>
</ServiceRequest>
"""

QUALYS_DOMAIN = 'Qualys_Domain'
USERNAME = 'username'
PASSWORD = 'password'


class QualysAdapter(AdapterBase):

    def _get_client_id(self, client_config):
        return client_config['Qualys_Domain']

    def _connect_client(self, client_config):
        try:
            connection = qualys_connection.QualysConnection(logger=self.logger, domain=client_config["Qualys_Domain"])
            connection.set_credentials(username=client_config["username"], password=client_config["password"])
            with connection:
                pass
            return connection
        except qualys_exceptions.QualysException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['Qualys_Domain'], str(e))
            self.logger.error(message)
            raise axonius.adapter_exceptions.ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Qualys domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Qualys connection

        :return: A json with all the attributes returned from the Qualys Server
        """
        with client_data:
            last_id = 0
            has_more_records = 'true'
            client_list = []
            while has_more_records == 'true':
                current_iterator_data = QUALYS_ITERATOR_FORMAT.format(last_id, 1000)
                current_clients_page = client_data.get_device_iterator(data=current_iterator_data)
                client_list.extend(current_clients_page['data'])
                last_id = current_clients_page.get('lastId', None)
                has_more_records = current_clients_page['hasMoreRecords']
            return client_list

    def _clients_schema(self):
        """
        The schema QualysAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "properties": {
                QUALYS_DOMAIN: {
                    "type": "string",
                    "name": "Qualys Domain"
                },
                USERNAME: {
                    "type": "string",
                    "name": "Username"
                },
                PASSWORD: {
                    "type": "password",
                    "name": "Password"
                }
            },
            "required": [
                QUALYS_DOMAIN,
                USERNAME,
                PASSWORD
            ],
            "type": "object"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device_raw = device_raw['HostAsset']
            if 'STATUS_ACTIVE' != device_raw['agentInfo']['status']:
                continue
            device_parsed = dict()
            device_parsed['hostname'] = device_raw['name']
            device_parsed['OS'] = figure_out_os(device_raw['os'])
            ifaces = device_raw['networkInterface']['list']
            iface_dict = []
            for mac, ip_ifaces in groupby(ifaces, lambda i: i['HostAssetInterface']['macAddress']):
                iface_dict.append({'MAC': mac, 'IP': [ip_iface['HostAssetInterface']['address']
                                                      for ip_iface in ip_ifaces]})

            device_parsed['network_interfaces'] = iface_dict
            device_parsed['id'] = device_raw['agentInfo']['agentId']
            device_parsed['raw'] = device_raw
            yield device_parsed

    def _correlation_cmds(self):
        """
        Correlation commands for Qualys
        :return: shell commands that help correlations
        """

        self.logger.error("correlation_cmds is not implemented for qualys adapter")
        raise NotImplementedError("correlation_cmds is not implemented for qualys adapter")

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        """
        Parses (very easily) the correlation cmd result, or None if failed
        :type correlation_cmd_result: str
        :param correlation_cmd_result: result of running cmd on a machine
        :type os_type: str
        :param os_type: the type of machine ran upon
        :return:
        """
        self.logger.error("_parse_correlation_results is not implemented for qualys adapter")
        raise NotImplementedError("_parse_correlation_results is not implemented for qualys adapter")
