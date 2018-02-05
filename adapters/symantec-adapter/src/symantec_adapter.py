"""
symantec_adapter.py: An adapter for Symantec Dashboard.
"""

__author__ = "Asaf & Tal"

from axonius.device import Device
import axonius.adapter_exceptions
from axonius.adapter_base import AdapterBase
import symantec_connection
import symantec_exceptions


class SymantecAdapter(AdapterBase):

    class MyDevice(Device):
        pass

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
            self.logger.exception(message)
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
                self.logger.info(f"Got {page_num*1000} devices so far")
            return client_list

    def _clients_schema(self):
        """
        The schema SymantecAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "SEPM_Address",
                    "title": "Symantec Endpoint Management Address",
                    "type": "string"
                },
                {
                    "name": "SEPM_Port",
                    "title": "Port",
                    "description": "Symantec Endpoint Management Port (Default is 8446)",
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
                "SEPM_Address",
                "username",
                "password"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            if 0 == device_raw['onlineStatus']:
                continue
            device = self._new_device()
            if device_raw.get('domainOrWorkgroup', '') == 'WORKGROUP' or device_raw.get('domainOrWorkgroup', '') == '':
                # Special case for workgroup
                device.hostname = device_raw.get('computerName', '')
            else:
                device.hostname = device_raw.get('computerName', '') + '.' + device_raw.get('domainOrWorkgroup', '')
            device.figure_os(' '.join([device_raw.get("operatingSystem", ''),
                                       str(device_raw.get("osbitness", '')),
                                       str(device_raw.get("osversion", '')),
                                       str(device_raw.get("osmajor", '')),
                                       str(device_raw.get("osminor", ''))]))
            for mac, ips in list(zip(device_raw.get('macAddresses', ''), device_raw.get('ipAddresses', ''))):
                device.add_nic(mac, ips, self.logger)

            device.id = device_raw['agentId']
            device.set_raw(device_raw)
            yield device

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
