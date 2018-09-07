import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_date
from minerva_adapter.connection import MinervaConnection

logger = logging.getLogger(f'axonius.{__name__}')


class MinervaAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')
        agent_status = Field(str, 'Agent Status')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get("domain"))

    def _connect_client(self, client_config):
        try:
            connection = MinervaConnection(domain=client_config["domain"], verify_ssl=client_config["verify_ssl"],
                                           username=client_config["username"], password=client_config["password"],
                                           url_base_prefix="owl/api/", headers={'Content-Type': 'application/json'})
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except RESTException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        try:
            client_data.connect()
            yield from client_data.get_device_list()
        finally:
            client_data.close()

    def _clients_schema(self):
        """
        The schema MinervaAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "domain",
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
                    "name": "verify_ssl",
                    "title": "Verify SSL",
                    "type": "bool"
                }
            ],
            "required": [
                "domain",
                "username",
                "password",
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
                except Exception:
                    logger.exception("Problem with adding nic to Minerva device")
                device.agent_version = device_raw.get("armorVersion", "")
                device.agent_status = device_raw.get("agentStatus")
                device.last_used_users = device_raw.get("loggedOnUsers", "").split(";")
                device.last_seen = parse_date(device_raw.get("lastSeenOnline", ""))
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception("Problem with fetching Minerva Device")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
