import logging
logger = logging.getLogger(f'axonius.{__name__}')
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.clients.rest.exception import RESTException
from secdo_adapter.connection import SecdoConnection
import datetime
from axonius.clients.rest.connection import RESTConnection


class SecdoAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        agent_state = Field(str, 'Agent State')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get("domain"))

    def _connect_client(self, client_config):
        try:
            connection = SecdoConnection(domain=client_config["domain"], verify_ssl=client_config["verify_ssl"],
                                         company=client_config["company"], apikey=client_config["apikey"],
                                         url_base_prefix="",
                                         headers={'Content-Type': 'application/json', "COMMAND-NAME": "get_agents",
                                                  "API-KEY": client_config["apikey"]})
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
        The schema SecdoAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "domain",
                    "title": "Secdo Domain",
                    "type": "string"
                },
                {
                    "name": "company",
                    "title": "Company Name",
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
                }
            ],
            "required": [
                "domain",
                "company",
                "apikey",
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
                    logger.warning(f'Bad device with no ID {device_raw}')
                    continue
                device.id += device_raw.get("hostName") or ''
                domain = device_raw.get("domain")
                if domain is None or domain == "" or domain.upper() == "N/A":
                    domain = None
                device.domain = domain
                device.hostname = device_raw.get("hostName")
                if domain is not None:
                    device.hostname = f"{device.hostname}.{domain}"
                device.figure_os(device_raw.get("osName", ""))
                try:
                    device.add_nic(None, device_raw.get("interfaces", "").split(","))
                except Exception:
                    logger.exception("Problem with fetching Secdo Device nic")
                device.add_agent_version(agent=AGENT_NAMES.secdo, version=device_raw.get("version", ""))
                device.agent_state = device_raw.get("agentState")
                device.last_used_users = device_raw.get("users", "").split(",")
                device.last_seen = datetime.datetime.fromtimestamp(max(device_raw.get("lastWatchdog", 0),
                                                                       device_raw.get("lastKeepAlive", 0), device_raw.get("lastTransmission", 0)))
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f"Problem with fetching Secdo Device for {device_raw}")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
