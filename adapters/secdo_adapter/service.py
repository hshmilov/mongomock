from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field

from secdo_adapter.connection import SecdoConnection
from secdo_adapter.exceptions import SecdoException
import json
import datetime


class SecdoAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')
        agent_state = Field(str, 'Agent State')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['Secdo_Domain']

    def _connect_client(self, client_config):
        try:
            connection = SecdoConnection(
                logger=self.logger, domain=client_config["Secdo_Domain"], verify_ssl=client_config["verify_ssl"])
            connection.set_credentials(company=client_config["company"], api_key=client_config["api_key"])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except SecdoException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['Secdo_Domain'], str(e))
            self.logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Secdo domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Secdo connection

        :return: A json with all the attributes returned from the Secdo Server
        """
        with client_data:
            return client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema SecdoAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "Secdo_Domain",
                    "title": "Secdo Domain",
                    "type": "string"
                },
                {
                    "name": "company",
                    "title": "Company Name",
                    "type": "string"
                },
                {
                    "name": "api_key",
                    "title": "API Key",
                    "type": "string"
                },
                {
                    "name": "verify_ssl",
                    "title": "Verify SSL",
                    "type": "bool"
                }
            ],
            "required": [
                "Secdo_Domain",
                "company",
                "api_key",
                "verify_ssl"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device.id = device_raw.get("agentId")
                if device.id is None:
                    continue
                device.hostname = device_raw.get("hostName")
                device.domain = device_raw.get("domain")
                device.figure_os(device_raw.get("osName", ""))
                try:
                    device.add_nic(None, device_raw.get("interfaces", "").split(","), self.logger)
                except:
                    self.logger.exception("Problem with fetching Secdo Device nic")
                device.agent_version = device_raw.get("version", "")
                device.agent_state = device_raw.get("agentState")
                device.last_used_users = device_raw.get("users", "").split(",")
                device.last_seen = datetime.datetime.fromtimestamp(max(device_raw.get("lastWatchdog", 0),
                                                                       device_raw.get("lastKeepAlive", 0), device_raw.get("lastTransmission", 0)))
                device.set_raw(device_raw)
                yield device
            except:
                self.logger.exception("Problem with fetching Secdo Device")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
