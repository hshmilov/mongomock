"""
SentinelOneAdapter.py: An adapter for SentinelOne Dashboard.
"""

__author__ = "Asaf & Tal"

from axonius.device import Device
import axonius.adapter_exceptions
from axonius.adapter_base import AdapterBase
import sentinelone_connection
import sentinelone_exceptions
import re


"""
OS types - should be moved to configuration
"""
WINDOWS_NAME = 'Windows'
OSX_NAME = 'macOS'
LINUX_NAME = 'Linux'

"""
Matches SentinelOne IDs
"""
sentinelone_ID_Matcher = {
    WINDOWS_NAME: re.compile('[a-fA-F0-9]{40}'),
    OSX_NAME: re.compile('[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}'),
    LINUX_NAME: re.compile('[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}')
}


class SentinelOneAdapter(AdapterBase):

    class MyDevice(Device):
        pass

    def _get_client_id(self, client_config):
        return client_config['SentinelOne_Domain']

    def _connect_client(self, client_config):
        try:
            domain = client_config["SentinelOne_Domain"]
            if domain in client_config:
                self.logger.info("Different logins for SentinelOne domain {0}, user: {1}",
                                 client_config["SentinelOne_Domain"], client_config["username"])
            connection = sentinelone_connection.SentinelOneConnection(logger=self.logger,
                                                                      domain=client_config["SentinelOne_Domain"])
            connection.set_credentials(username=client_config["username"], password=client_config["password"])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except sentinelone_exceptions.SentinelOneException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['SentinelOne_Domain'], str(e))
            self.logger.exception(message)
            raise axonius.adapter_exceptions.ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific SentinelOne domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a SentinelOne connection

        :return: A json with all the attributes returned from the SentinelOne Server
        """
        with client_data:
            current_clients_page = client_data.get_device_iterator(limit='200')
            client_list = current_clients_page['data']
            last_id = current_clients_page['last_id']
            while last_id is not None:
                current_clients_page = client_data.get_device_iterator(limit='200', last_id=last_id)
                client_list.extend(current_clients_page['data'])
                last_id = current_clients_page['last_id']
            return client_list

    def _clients_schema(self):
        """
        The schema SentinelOneAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "properties": {
                "SentinelOne_Domain": {
                    "type": "string",
                    "name": "Sentinel One Domain"
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
                "SentinelOne_Domain",
                "username",
                "password"
            ],
            "type": "object"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            if not device_raw['is_active']:
                continue
            soft_info = device_raw['software_information']
            net_info = device_raw['network_information']
            device = self._new_device()
            device.hostname = net_info['computer_name'] + '.' + net_info['domain']
            device.figure_os(' '.join([soft_info['os_name'], soft_info['os_arch'], soft_info['os_revision']]))
            for interface in net_info['interfaces']:
                device.add_nic(interface['physical'], interface['inet6'] + interface['inet'], self.logger)
            device.id = device_raw['id']
            device.set_raw(device_raw)
            yield device

    def _correlation_cmds(self):
        """
        Correlation commands for SentinelOne
        :return: shell commands that help correlations
        """

        # Both the agent id and the agent unique id remain intact when uninstalling
        # We chose the uuid as it's a globally unique id and not a mongoDB one
        # return {
        #     WINDOWS_NAME: r"""
        #                 Powershell -Command "& invoke-command -ScriptBlock {$bla = Get-ItemPropertyValue Registry::'HKLM\SYSTEM\CurrentControlSet\Services\SentinelMonitor\Config' -Name InProcessClientsDir; cmd /c "`\"${bla}SentinelCtl.exe`\" agent_id"}"
        #                """.strip(),
        #     OSX_NAME: """system_profiler SPHardwareDataType | awk '/UUID/ { print $3; }'""",
        #     LINUX_NAME: """cat /sys/class/dmi/id/product_uuid"""
        # }
        raise NotImplementedError('; cannot be used as a separator')

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        """
        Parses (very easily) the correlation cmd result, or None if failed
        :type correlation_cmd_result: str
        :param correlation_cmd_result: result of running cmd on a machine
        :type os_type: str
        :param os_type: the type of machine ran upon
        :return:
        """
        if os_type in sentinelone_ID_Matcher:
            return next(sentinelone_ID_Matcher[os_type].findall(correlation_cmd_result.strip()), None)
        else:
            self.logger.warn("The OS type {0} doesn't have a sentinelone matcher", os_type)
            return None
