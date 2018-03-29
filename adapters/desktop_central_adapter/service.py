import json

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from desktop_central_adapter.connection import DesktopCentralConnection
from desktop_central_adapter.exceptions import DesktopCentralException


class DesktopCentralAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')
        installation_status = Field(str, 'Installation Status')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['DesktopCentral_Domain']

    def _connect_client(self, client_config):
        try:
            domain = client_config["DesktopCentral_Domain"]
            connection = DesktopCentralConnection(logger=self.logger,
                                                  domain=client_config["DesktopCentral_Domain"], verify_ssl=client_config["verify_ssl"])
            connection.set_credentials(username=client_config["username"], password=client_config["password"])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except DesktopCentralException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['DesktopCentral_Domain'], str(e))
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific DesktopCentral domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a DesktopCentral connection

        :return: A json with all the attributes returned from the DesktopCentral Server
        """
        with client_data:
            return client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema DesktopCentralAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "DesktopCentral_Domain",
                    "title": "Desktop Central Domain",
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
                "DesktopCentral_Domain",
                "username",
                "password",
                "veirfy_ssl"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                # 2 represents live_status is down
                if device_raw.get("computer_live_status", device_raw.get("live_status")) == 2:
                    continue
                # 22 Means installed
                # In case there is no such field we don't want to miss the device
                device = self._new_device_adapter()
                device.domain = device_raw.get("domain_netbios_name", "")
                device.hostname = device_raw.get("full_name", "")
                device.figure_os(' '.join([device_raw.get("os_name", ""),
                                           device_raw.get("service_pack", "")]))
                try:
                    if device_raw.get("mac_address") or device_raw.get("ip_address"):
                        device.add_nic(device_raw.get("mac_address"), device_raw.get(
                            "ip_address", "").split(","), self.logger)
                except:
                    self.logger.exception("Problem with adding nic to desktop central device")
                device.agent_version = device_raw.get("agent_version", "")
                if "resource_id" not in device_raw:
                    self.logger.info(f"No Desktop Central device Id for {str(device_raw)}")
                    continue
                device.id = str(device_raw.get("resource_id"))
                os_version_list = device_raw.get("os_version", "").split(".")
                device.os.major = int(os_version_list[0])
                if len(os_version_list) > 1:
                    device.os.minor = int(os_version_list[1])
                device.installation_status = device_raw.get("installation_status")
                installation_status = device_raw.get("installation_status")
                if installation_status is not None:
                    device.installation_status = {21: "Yet to install", 22: "Installed",
                                                  23: "uninstalled", 24: "yet to uninstall",
                                                  29: "installation failure"}.get(installation_status)
                device.last_used_users = device_raw.get("agent_logged_on_users", "").split(",")
                device.set_raw(device_raw)
                yield device
            except:
                self.logger.exception("Problem with fetching Desktop Central Device")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Manager, AdapterProperty.Agent]
