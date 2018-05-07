import logging
logger = logging.getLogger(f"axonius.{__name__}")
import re

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file

from sentinelone_adapter.connection import SentinelOneConnection
from sentinelone_adapter.exceptions import SentinelOneException
from axonius.fields import Field
from axonius.utils.parsing import parse_date


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


class SentineloneAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')
        active_state = Field(str, 'Active State')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['SentinelOne_Domain']

    def _connect_client(self, client_config):
        has_token = bool(client_config.get('token'))
        maybe_has_user = bool(client_config.get('username')) or bool(client_config.get('password'))
        has_user = bool(client_config.get('username')) and bool(client_config.get('password'))
        if has_token and maybe_has_user:
            msg = f"Different logins for SentinelOne domain " \
                  f"{client_config.get('SentinelOne_Domain')}, user: {client_config.get('username', '')}"
            logger.error(msg)
            raise ClientConnectionException(msg)
        elif maybe_has_user and not has_user:
            msg = f"Missing credentials for SentinelOne domain " \
                  f"{client_config.get('SentinelOne_Domain')}, user: {client_config.get('username', '')}"
            logger.error(msg)
            raise ClientConnectionException(msg)
        try:
            connection = SentinelOneConnection(domain=client_config["SentinelOne_Domain"])
            if has_token:
                connection.set_token(client_config['token'])
            else:
                connection.set_credentials(username=client_config["username"], password=client_config["password"])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except SentinelOneException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['SentinelOne_Domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific SentinelOne domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a SentinelOne connection

        :return: A json with all the attributes returned from the SentinelOne Server
        """
        with client_data:
            devices_count = 0
            current_clients_page = client_data.get_device_iterator(limit='200')
            client_list = current_clients_page['data']
            last_id = current_clients_page['last_id']
            while last_id is not None:
                devices_count += 1
                logger.info(f"Got {devices_count*200} devices so far")
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
            "items": [
                {
                    "name": "SentinelOne_Domain",
                    "title": "Sentinel One Domain",
                    "type": "string"
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
                },
                {
                    "name": "token",
                    "title": "API token",
                    "type": "string"
                },
            ],
            "required": [
                "SentinelOne_Domain"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            soft_info = device_raw.get('software_information', {})
            net_info = device_raw.get('network_information', {})
            device = self._new_device_adapter()
            computer_name, domain = net_info.get('computer_name'), net_info.get('domain')
            if computer_name is not None:
                hostname = computer_name
                if domain is not None:
                    hostname = f"{hostname}.{domain}"
                device.hostname = hostname
            device.domain = net_info.get('domain')
            device.figure_os(' '.join([soft_info.get('os_name', ''), soft_info.get(
                'os_arch', ''), soft_info.get('os_revision', '')]))
            try:
                for interface in net_info.get('interfaces', []):
                    device.add_nic(interface.get('physical'), interface.get(
                        'inet6', []) + interface.get('inet', []))
            except Exception:
                logger.exception(f"Problem adding nic {str(interfaces)} to SentinelOne")
            device.agent_version = device_raw.get('agent_version')
            device.id = device_raw['id']
            device.last_seen = parse_date(str(device_raw.get('last_active_date', '')))
            device.active_state = device_raw.get('is_active')
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
            logger.warn("The OS type {0} doesn't have a sentinelone matcher", os_type)
            return None

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
