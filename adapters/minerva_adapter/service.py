from axonius.adapter_base import AdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device import Device
from axonius.utils.files import get_local_config_file
from axonius.fields import Field

from minerva_adapter.connection import MinervaConnection
from minerva_adapter.exceptions import MinervaException
import json
from axonius.parsing_utils import parse_date


class MinervaAdapter(AdapterBase):

    class MyDevice(Device):
        agent_version = Field(str, 'Agent Version')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['Minerva_Domain']

    def _connect_client(self, client_config):
        try:
            domain = client_config["Minerva_Domain"]
            if domain in client_config:
                self.logger.info("Different logins for Minerva domain {0}, user: {1}",
                                 client_config["Minerva_Domain"], client_config["username"])
            connection = MinervaConnection(logger=self.logger, domain=client_config["Minerva_Domain"],
                                           is_ssl=client_config["is_ssl"])
            connection.set_credentials(username=client_config["username"], password=client_config["password"])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except MinervaException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['Minerva_Domain'], str(e))
            self.logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Minerva domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Minerva connection

        :return: A json with all the attributes returned from the Minerva Server
        """
        with client_data:
            return json.dumps(client_data.get_device_list())

    def _clients_schema(self):
        """
        The schema MinervaAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "Minerva_Domain",
                    "title": "Minerva Domain",
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
                    "name": "is_ssl",
                    "title": "Is SSL",
                    "type": "bool"
                }
            ],
            "required": [
                "Minerva_Domain",
                "username",
                "password",
                "is_ssl"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in json.loads(devices_raw_data):
            try:
                if device_raw.get("agentStatus", "Online") != "Online":
                    continue
                device = self._new_device()
                device.id = device_raw.get("id")
                if device.id == None:
                    continue
                device.hostname = device_raw.get("endpoint")
                device.figure_os(device_raw.get("operatingSystem", ""))
                device.add_nic(None, device_raw.get("reportedIpAddress", "").split(","), self.logger)
                device.agent_version = device_raw.get("armorVersion", "")
                device.last_used_users = device_raw.get("loggedOnUsers", "").split(",")
                device.last_seen = parse_date(device_raw.get("lastSeenOnline", ""))
                device.set_raw(device_raw)
                yield device
            except:
                self.logger.exception("Problem with fetching Minerva Device")
