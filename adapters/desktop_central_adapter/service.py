import logging
logger = logging.getLogger(f'axonius.{__name__}')

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from desktop_central_adapter.connection import DesktopCentralConnection
from axonius.clients.rest.exception import RESTException
from desktop_central_adapter import consts
import datetime


class DesktopCentralAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')
        installation_status = Field(str, 'Installation Status')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _connect_client(self, client_config):
        try:
            connection = DesktopCentralConnection(domain=client_config["domain"],
                                                  verify_ssl=client_config["verify_ssl"],
                                                  username=client_config["username"], password=client_config["password"],
                                                  url_base_prefix="api/1.0", headers={'Content-Type': 'application/json'},
                                                  https_proxy=client_config.get("https_proxy"),
                                                  http_proxy=client_config.get("http_proxy"),
                                                  port=client_config.get("port", consts.DEFAULT_PORT),
                                                  username_domain=client_config.get("username_domain"))
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
        The schema the adapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "domain",
                    "title": "Desktop Central Domain",
                    "type": "string"
                },
                {
                    "name": "username",
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": "username_domain",
                    "title": "Username Domain",
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
                },
                {
                    "name": "http_proxy",
                    "title": "HTTP Proxy",
                    "type": "string"
                },
                {
                    "name": "https_proxy",
                    "title": "HTTPS Proxy",
                    "type": "string"
                }
            ],
            "required": [
                "domain",
                "username",
                "password",
                "veirfy_ssl"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                # 22 Means installed
                # In case there is no such field we don't want to miss the device

                device = self._new_device_adapter()
                property_none_list = []
                for property in device_raw:
                    if device_raw[property] == "--":
                        property_none_list.append(property)
                for property in property_none_list:
                    del device_raw[property]
                if "resource_id" not in device_raw:
                    logger.info(f"No Desktop Central device Id for {str(device_raw)}")
                    continue
                device.id = str(device_raw.get("resource_id"))
                device.domain = device_raw.get("domain_netbios_name", "")
                device.hostname = device_raw.get("fqdn_name", device_raw.get("full_name"))
                try:
                    last_seen = device_raw.get("agent_last_contact_time")
                    if last_seen is not None:
                        device.last_seen = datetime.datetime.fromtimestamp(last_seen / 1000)
                except Exception:
                    logger.exception(f"Problem getting last seen for {device_raw}")
                device.figure_os(' '.join([device_raw.get("os_name", ""),
                                           device_raw.get("service_pack", "")]))
                try:
                    if device_raw.get("mac_address") or device_raw.get("ip_address"):
                        mac_addresses = (device_raw.get("mac_address") or '').split(',')
                        ips = (device_raw.get("ip_address") or '').split(",")
                        if not mac_addresses:
                            device.add_nic(None, ips)
                        else:
                            for mac_address in mac_addresses:
                                device.add_nic(mac_address, ips)
                except Exception:
                    logger.exception("Problem with adding nic to desktop central device")
                device.agent_version = device_raw.get("agent_version", "")
                try:
                    os_version_list = device_raw.get("os_version", "").split(".")
                    device.os.major = int(os_version_list[0])
                except Exception:
                    logger.exception(f"Problem getting major os for {os_version_list}")
                try:
                    if len(os_version_list) > 1 and "(" not in os_version_list[1]:
                        device.os.minor = int(os_version_list[1])
                except Exception:
                    logger.exception(f"Problem getting minor os for {os_version_list}")
                device.installation_status = device_raw.get("installation_status")
                installation_status = device_raw.get("installation_status")
                if installation_status is not None:
                    device.installation_status = {21: "Yet to install", 22: "Installed",
                                                  23: "uninstalled", 24: "yet to uninstall",
                                                  29: "installation failure"}.get(installation_status)
                device.last_used_users = device_raw.get("agent_logged_on_users", "").split(",")
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception("Problem with fetching Desktop Central Device")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
