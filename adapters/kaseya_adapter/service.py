import logging
logger = logging.getLogger(f'axonius.{__name__}')
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field

from kaseya_adapter.connection import KaseyaConnection
from kaseya_adapter.exceptions import KaseyaException
from axonius.utils.parsing import parse_date


class KaseyaAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')
        agent_status = Field(str, 'Agent Status')
        agent_id = Field(str, "Agent ID")

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['Kaseya_Domain']

    def _connect_client(self, client_config):
        try:
            connection = KaseyaConnection(domain=client_config["Kaseya_Domain"], verify_ssl=client_config["verify_ssl"])
            connection.set_credentials(username=client_config["username"], password=client_config["password"])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except KaseyaException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['Kaseya_Domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Kaseya domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Kaseya connection

        :return: A json with all the attributes returned from the Kaseya Server
        """
        with client_data:
            return client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema KaseyaAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "Kaseya_Domain",
                    "title": "Kaseya Domain",
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
                "Kaseya_Domain",
                "username",
                "password",
                "verify_ssl"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, agents_assets_raw_data):
        assets_raw_data = agents_assets_raw_data['assets']
        agents_id_dict = agents_assets_raw_data['agents']
        for asset_raw in assets_raw_data:
            try:
                device = self._new_device_adapter()
                device.id = asset_raw.get("AssetId")
                if device.id is None:
                    continue
                device.id = str(device.id)
                device.name = asset_raw.get("AssetName")
                agent_raw = agents_id_dict.get(asset_raw.get("AgentId", "-1"), {})
                device.figure_os(asset_raw.get("OSName", ""))
                device.hostname = agent_raw.get("ComputerName", asset_raw.get("HostName"))
                try:
                    last_used_users = agent_raw.get("LastLoggedInUser")
                    if last_used_users is not None:
                        device.last_used_users = last_used_users.split(",")
                except Exception:
                    logger.exception(f"Problem with gettng users in {agent_raw}")
                try:
                    agent_last_seen = parse_date(str(agent_raw.get("LastCheckInTime", "")))
                    asset_last_seen = parse_date(str(asset_raw.get("LastSeenDate", "")))
                    if asset_last_seen is not None and agent_last_seen is not None:
                        device.last_seen = max(asset_last_seen, agent_last_seen)
                    elif asset_last_seen is not None or agent_last_seen is not None:
                        device.last_seen = asset_last_seen or agent_last_seen
                except Exception:
                    logger.exception(f"Problem getting last seend in asset: {asset_raw} and agent: {agent_raw}")
                device.time_zone = agent_raw.get("TimeZone")
                try:
                    device.total_physical_memory = int(agent_raw.get("RamMBytes", 0)) / (1024 * 1.0)
                except Exception:
                    logger.exception(f"Problem  adding time zone to {agent_raw}")
                device.device_manufacturer = asset_raw.get("DeviceManufacturer")
                ip_addresses = asset_raw.get("IPAddresses", "").split(",")
                mac_addresses = asset_raw.get("MACAddresses", "").split(",")
                if mac_addresses != []:
                    for mac_address in mac_addresses:
                        device.add_nic(mac_address, ip_addresses)
                elif ip_addresses != []:
                    device.add_nic(None, ip_addresses)
                device.agent_id = str(agent_raw.get("AgentId", ""))
                device.agent_version = str(agent_raw.get("AgentVersion", ""))
                device.agent_status = str(agent_raw.get("Online", ""))
                device.set_raw(agents_assets_raw_data)
                yield device
            except Exception:
                logger.exception("Problem with fetching Kaseya Device")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Manager]
