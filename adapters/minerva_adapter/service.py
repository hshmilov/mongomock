import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field

from minerva_adapter.connection import MinervaConnection
from minerva_adapter.exceptions import MinervaException
from axonius.utils.parsing import parse_date


class MinervaAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')
        agent_status = Field(str, 'Agent Status')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['Minerva_Domain']

    def _connect_client(self, client_config):
        try:
            connection = MinervaConnection(domain=client_config["Minerva_Domain"],
                                           is_ssl=client_config["is_ssl"], verify_ssl=client_config["verify_ssl"])
            connection.set_credentials(username=client_config["username"],
                                       password=self.decrypt_password(client_config["password"]))
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except MinervaException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['Minerva_Domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Minerva domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Minerva connection

        :return: A json with all the attributes returned from the Minerva Server
        """
        with client_data:
            return client_data.get_device_list()

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
                },
                {
                    "name": "verify_ssl",
                    "title": "Verify SSL",
                    "type": "bool"
                }
            ],
            "required": [
                "Minerva_Domain",
                "username",
                "password",
                "is_ssl",
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
                device.hostname = device_raw.get("endpoint")
                device.figure_os(device_raw.get("operatingSystem", ""))
                try:
                    if device_raw.get("reportedIpAddress"):
                        device.add_nic(None, device_raw.get("reportedIpAddress", "").split(","))
                except:
                    logger.exception("Problem with adding nic to Minerva device")
                device.agent_version = device_raw.get("armorVersion", "")
                device.agent_status = device_raw.get("agentStatus")
                device.last_used_users = device_raw.get("loggedOnUsers", "").split(";")
                device.last_seen = parse_date(device_raw.get("lastSeenOnline", ""))
                device.set_raw(device_raw)
                yield device
            except:
                logger.exception("Problem with fetching Minerva Device")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
