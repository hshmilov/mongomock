from axonius.adapter_base import AdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device import Device
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from symantec_adapter.connection import SymantecConnection
from symantec_adapter.exceptions import SymantecException
import datetime


class SymantecAdapter(AdapterBase):

    class MyDevice(Device):
        online_status = Field(str, 'Online Status')
        agent_version = Field(str, 'Agent Version')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['SEPM_Address']

    def _connect_client(self, client_config):
        try:
            connection = SymantecConnection(logger=self.logger, domain=client_config["SEPM_Address"],
                                            port=(client_config["SEPM_Port"] if "SEPM_Port" in client_config else None))
            connection.set_credentials(username=client_config["username"], password=client_config["password"])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except SymantecException as e:
            message = "Error connecting to client with address {0} and port {1}, reason: {2}".format(
                client_config['SEPM_Address'], client_config['SEPM_Port'], str(e))
            self.logger.exception(message)
            raise ClientConnectionException(message)

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
            try:
                mac_addresses = device_raw.get('macAddresses', [])
                ip_addresses = device_raw.get('ipAddresses')
                if mac_addresses == []:
                    device.add_nic(None, ip_addresses, self.logger)
                for mac_address in mac_addresses:
                    device.add_nic(mac_address, ip_addresses, self.logger)
            except:
                self.logger.exception("Problem adding nic to Symantec")
            device.online_status = str(device_raw.get('onlineStatus'))
            device.agent_version = device_raw.get("agentVersion")
            try:
                device.last_seen = datetime.datetime.fromtimestamp(max(int(device_raw.get("lastScanTime", 0)),
                                                                       int(device_raw.get("lastUpdateTime", 0))) / 1000)
            except:
                self.logger.exception("Problem adding last seen to Symantec")
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
