import logging
logger = logging.getLogger(f'axonius.{__name__}')
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field

from carbonblack_protection_adapter.connection import CarbonblackProtectionConnection
from carbonblack_protection_adapter.exceptions import CarbonblackProtectionException
import json
from axonius.utils.parsing import parse_date
import datetime


class CarbonblackProtectionAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        connected = Field(bool, "Connected")
        agent_version = Field(str, 'Agent Version')
        policy_name = Field(str, 'Policy Name')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['CarbonblackProtection_Domain']

    def _connect_client(self, client_config):
        try:
            connection = CarbonblackProtectionConnection(
                domain=client_config["CarbonblackProtection_Domain"],
                verify_ssl=client_config["verify_ssl"], https_proxy=client_config.get("https_proxy"))
            connection.set_credentials(apikey=client_config["apikey"])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except CarbonblackProtectionException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['CarbonblackProtection_Domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific CarbonblackProtection domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a CarbonblackProtection connection

        :return: A json with all the attributes returned from the CarbonblackProtection Server
        """
        with client_data:
            return client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema CarbonblackProtectionAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "CarbonblackProtection_Domain",
                    "title": "Carbonblack Protection Domain",
                    "type": "string"
                },
                {
                    "name": "apikey",
                    "title": "API Key",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": "verify_ssl",
                    "title": "Verify SSL",
                    "type": "bool"
                },
                {
                    "name": "https_proxy",
                    "title": "Https Proxy",
                    "type": "string"
                }

            ],
            "required": [
                "CarbonblackProtection_Domain",
                "apikey",
                "verify_ssl"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device.id = device_raw.get("id")
                if device.id is None:
                    continue
                else:
                    device.id = str(device.id)
                hostname = device_raw.get("name")
                if hostname and '\\' in hostname:
                    split_hostname = hostname.split('\\')
                    device.hostname = split_hostname[1]
                    device.domain = split_hostname[0]
                    device.part_of_domain = True
                else:
                    device.hostname = hostname
                device.description = device_raw.get("description")
                device.figure_os((device_raw.get("osShortName") or "") + " " + (device_raw.get("osName") or ""))
                try:
                    if device_raw.get("ipAddress", "") != "" or device_raw.get("macAddress", "") != "":
                        device.add_nic(device_raw.get("macAddress"), device_raw.get("ipAddress", "").split(","))
                except Exception:
                    logger.exception("Problem with adding nic to CarbonblackProtection device")
                try:
                    device.last_seen = parse_date(str(device_raw.get("lastPollDate")))
                except Exception:
                    logger.exception("Problem getting Last seen in CarbonBlackProtection")
                device.agent_version = device_raw.get("agentVersion")
                device.policy_name = device_raw.get("policyName")
                device.last_used_users = str(device_raw.get("users", "")).split(",")
                device.connected = device_raw.get("connected")
                total_physical_memory = device_raw.get("memorySize")
                if total_physical_memory is not None:
                    device.total_physical_memory = int(total_physical_memory) / 1024.0
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception("Problem with fetching CarbonblackProtection Device")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
