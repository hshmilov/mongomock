"""
symantec_adapter.py: An adapter for Symantec Dashboard.
"""

__author__ = "Asaf & Tal"

import axonius.adapter_exceptions
from axonius.adapter_base import AdapterBase
from axonius.parsing_utils import figure_out_os
import symantec_connection
import symantec_exceptions


class SymantecAdapter(AdapterBase):

    def _get_client_id(self, client_config):
        return client_config['SEPM_Address']

    def _connect_client(self, client_config):
        try:
            connection = symantec_connection.SymantecConnection(logger=self.logger,
                                                                domain=client_config["SEPM_Address"],
                                                                port=(client_config["SEPM_Port"] if "SEPM_Port" in client_config else None))
            connection.set_credentials(username=client_config["username"], password=client_config["password"])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except symantec_exceptions.SymantecException as e:
            message = "Error connecting to client with address {0} and port {1}, reason: {2}".format(
                client_config['SEPM_Address'], client_config['SEPM_Port'], str(e))
            self.logger.error(message)
            raise axonius.adapter_exceptions.ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Symantec domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Symantec connection

        :return: A json with all the attributes returned from the Symantec Server
        """
        with client_data:
            page_num = 1
            client_list = []
            last_page = False
            while not last_page:
                current_clients_page = client_data.get_device_iterator(pageSize='1000', pageIndex=page_num)
                client_list.extend(current_clients_page['content'])
                last_page = current_clients_page['lastPage']
                page_num += 1
            return client_list

    def _clients_schema(self):
        """
        The schema SymantecAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "properties": {
                "SEPM_Address": {
                    "type": "string",
                    "name": "Symantec Endpoint Management Address"
                },
                "SEPM_Port": {
                    "type": "string",
                    "name": "Symantec Endpoint Management Port (Default is 8446)"
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
                "SEPM_Address",
                "username",
                "password"
            ],
            "type": "object"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            if 0 == device_raw['onlineStatus']:
                continue
            device_parsed = dict()
            device_parsed['hostname'] = device_raw['computerName'] + '.' + device_raw['domainOrWorkgroup']
            device_parsed['OS'] = figure_out_os(' '.join([device_raw["operatingSystem"],
                                                          str(device_raw["osbitness"]),
                                                          str(device_raw["osversion"]),
                                                          str(device_raw["osmajor"]),
                                                          str(device_raw["osminor"])]))
            device_parsed['network_interfaces'] = [{"MAC": mac, "IP": [IP]}
                                                   for mac, IP in list(zip(device_raw['macAddresses'], device_raw['ipAddresses']))]

            device_parsed['id'] = device_raw['agentId']
            device_parsed['raw'] = device_raw
            yield device_parsed

    def _correlation_cmds(self):
        """
        Correlation commands for Symantec
        :return: shell commands that help correlations
        """
        self.logger.error("correlation_cmds is not implemented for symantec adapter")
        raise NotImplementedError("correlation_cmds is not implemented for symantec adapter")

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        """
        Parses (very easily) the correlation cmd result, or None if failed
        :type correlation_cmd_result: str
        :param correlation_cmd_result: result of running cmd on a machine
        :type os_type: str
        :param os_type: the type of machine ran upon
        :return:
        """
        self.logger.error("_parse_correlation_results is not implemented for symantec adapter")
        raise NotImplementedError("_parse_correlation_results is not implemented for symantec adapter")
