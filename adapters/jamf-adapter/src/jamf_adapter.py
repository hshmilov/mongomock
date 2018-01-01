"""
JamfAdapter.py: An adapter for Jamf Dashboard.
"""
__author__ = "Asaf & Tal"

import axonius.adapter_exceptions
from axonius.adapter_base import AdapterBase
from axonius.parsing_utils import figure_out_os
import jamf_connection
import jamf_exceptions
import jamf_consts


class JamfAdapter(AdapterBase):

    def _get_client_id(self, client_config):
        return client_config['Jamf_Domain']

    def _connect_client(self, client_config):
        try:
            connection = jamf_connection.JamfConnection(logger=self.logger, domain=client_config["Jamf_Domain"])
            connection.set_credentials(username=client_config["username"], password=client_config["password"])
            connection.connect()
            return connection
        except jamf_exceptions.JamfException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['Jamf_Domain'], str(e))
            self.logger.error(message)
            raise axonius.adapter_exceptions.ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Jamf domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Jamf connection

        :return: A json with all the attributes returned from the Jamf Server
        """
        return client_data.get_devices()

    def _clients_schema(self):
        """
        The schema JamfAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "properties": {
                jamf_consts.JAMF_DOMAIN: {
                    "type": "string",
                    "name": "Jamf Domain"
                },
                jamf_consts.USERNAME: {
                    "type": "string",
                    "name": "Username"
                },
                jamf_consts.PASSWORD: {
                    "type": "password",
                    "name": "Password"
                }
            },
            "required": [
                jamf_consts.JAMF_DOMAIN,
                jamf_consts.USERNAME,
                jamf_consts.PASSWORD
            ],
            "type": "object"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device_parsed = dict()
            device_parsed['hostname'] = device_raw.get('name', '')
            device_parsed['id'] = device_raw.get('udid', '')
            if 'Operating_System' in device_raw:
                device_parsed['OS'] = figure_out_os(' '.join([device_raw.get('Operating_System', ''),
                                                              device_raw.get('Architecture_Type', '')
                                                              ]))
                device_parsed['network_interfaces'] = [{'MAC': device_raw.get('MAC_Address', ''),
                                                        'IP': [device_raw.get('IP_Address', '')]}]
                if device_raw['Last_Reported_IP_Address'] != '':
                    device_parsed['network_interfaces'].append({'MAC': device_raw.get('MAC_Address'),
                                                                'IP': [device_raw.get('Last_Reported_IP_Address', '')]})
            else:
                device_parsed['OS'] = figure_out_os(' '.join([device_raw.get('Model_Identifier', ''),
                                                              device_raw.get('iOS_Version', '')
                                                              ]))
                device_parsed['network_interfaces'] = [{'MAC': device_raw.get('Wi_Fi_MAC_Address'),
                                                        'IP': [device_raw.get('IP_Address')]}]
            device_parsed['raw'] = device_raw
            yield device_parsed

    def _correlation_cmds(self):
        """
        Correlation commands for Jamf
        :return: shell commands that help correlations
        """

        self.logger.error("correlation_cmds is not implemented for jamf adapter")
        raise NotImplementedError("correlation_cmds is not implemented for jamf adapter")

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        """
        Parses (very easily) the correlation cmd result, or None if failed
        :type correlation_cmd_result: str
        :param correlation_cmd_result: result of running cmd on a machine
        :type os_type: str
        :param os_type: the type of machine ran upon
        :return:
        """
        self.logger.error("_parse_correlation_results is not implemented for jamf adapter")
        raise NotImplementedError("_parse_correlation_results is not implemented for jamf adapter")
