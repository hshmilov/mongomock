from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device import Device
from axonius.utils.files import get_local_config_file
from axonius.fields import Field

from ensilo_adapter.connection import EnsiloConnection
from ensilo_adapter.exceptions import EnsiloException
import json
from axonius.parsing_utils import parse_date


class EnsiloAdapter(AdapterBase):

    class MyDevice(Device):
        agent_version = Field(str, 'Agent Version')
        state = Field(str, "Device running state")

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['Ensilo_Domain']

    def _connect_client(self, client_config):
        try:

            connection = EnsiloConnection(logger=self.logger, domain=client_config["Ensilo_Domain"],
                                          verify_ssl=client_config["verify_ssl"])
            connection.set_credentials(username=client_config["username"], password=client_config["password"])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except EnsiloException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['Ensilo_Domain'], str(e))
            self.logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Ensilo domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Ensilo connection

        :return: A json with all the attributes returned from the Ensilo Server
        """
        with client_data:
            return client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema EnsiloAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "Ensilo_Domain",
                    "title": "Ensilo Domain",
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
                "Ensilo_Domain",
                "username",
                "password",
                "verify_ssl"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device()
                device.id = device_raw.get("name")
                if device.id is None:
                    continue
                device.state = device_raw.get("state")
                device.hostname = device_raw.get("name")
                device.figure_os(device_raw.get("operatingSystem", ""))
                try:
                    mac_addresses = list(device_raw.get("macAddresses", []))
                    ip_addresses = device_raw.get("ipAddress")
                    if ip_addresses is not None:
                        ip_addresses = ip_addresses.split(",")
                    if mac_addresses == []:
                        if ip_addresses is not None:
                            device.add_nic(None, ip_addresses, self.logger)
                    else:
                        for mac_address in mac_addresses:
                            if ip_addresses is not None:
                                device.add_nic(mac_address, ip_addresses, self.logger)
                            else:
                                device.add_nic(mac_address, None, self.logger)
                except:
                    self.logger.exception("Problem with adding nic to ensilo device")
                device.agent_version = device_raw.get("version", "")
                device.last_seen = parse_date(str(device_raw.get("lastSeenTime", "")))
                device.set_raw(device_raw)
                yield device
            except:
                self.logger.exception("Problem with fetching Ensilo Device")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
