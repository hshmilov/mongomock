import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field

from airwatch_adapter.connection import AirwatchConnection
from airwatch_adapter.exceptions import AirwatchException

from axonius.utils.parsing import parse_date


class AirwatchAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        imei = Field(str, 'IMEI')
        phone_number = Field(str, 'Phone Number')
        udid = Field(str, 'UdId')
        friendly_name = Field(str, 'Device Friendly Name')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['Airwatch_Domain']

    def _connect_client(self, client_config):
        try:
            connection = AirwatchConnection(domain=client_config["Airwatch_Domain"],
                                            apikey=client_config["apikey"], verify_ssl=client_config["verify_ssl"])
            connection.set_credentials(username=client_config["username"], password=client_config["password"],
                                       apikey=client_config["apikey"])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except AirwatchException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['Airwatch_Domain'], str(e))
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Airwatch domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Airwatch connection

        :return: A json with all the attributes returned from the Airwatch Server
        """
        with client_data:
            return client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema AirwatchAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "Airwatch_Domain",
                    "title": "Airwatch Domain",
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
                    "name": "apikey",
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
                "Airwatch_Domain",
                "username",
                "password",
                "apikey",
                "verify_ssl"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                if not device_raw.get("Id"):
                    continue
                else:
                    device.id = str(device_raw.get("Id").get("Value"))
                device.imei = device_raw.get("Imei", "")
                device.last_seen = parse_date(str(device_raw.get("LastSeen", "")))
                device.figure_os(device_raw.get("Platform", "") + " " + device_raw.get("OperatingSystem", ""))
                device.phone_number = device_raw.get("PhoneNumber", "")
                try:
                    network_raw = device_raw.get("Network", {})
                    wifi_info = network_raw.get("WifiInfo", {})
                    mac_address = wifi_info.get("WifiMacAddress", device_raw.get("MacAddress"))
                    if mac_address == "" or mac_address == "0.0.0.0":
                        mac_address = None
                    ipaddresses_raw = network_raw.get("IPAddress")
                    ipaddresses = []
                    falsed_ips = ["0.0.0.0", "127.0.0.1", "", None]
                    for ipaddress_raw in ipaddresses_raw:
                        if ipaddresses_raw[ipaddress_raw] not in falsed_ips:
                            ipaddresses.append(ipaddresses_raw[ipaddress_raw])
                    if ipaddresses != [] or mac_address is not None:
                        device.add_nic(mac_address, ipaddresses)
                except Exception:
                    logger.exception("Problem adding nic to Airwatch")
                device.device_serial = device_raw.get("SerialNumber")
                device.udid = device_raw.get("Udid")

                device.friendly_name = device_raw.get("DeviceFriendlyName")
                device.last_used_users = device_raw.get("UserName", "").split(",")
                try:
                    for app_raw in device_raw.get("DeviceApps", []):
                        device.add_installed_software(name=app_raw.get("ApplicationName"),
                                                      version=app_raw.get("Version"))
                except Exception:
                    logger.exception("Problem adding software to Airwatch")
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception("Problem with fetching Airwatch Device")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
