import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from service_now_adapter.consts import *
from service_now_adapter.connection import ServiceNowConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.parsing import parse_date


class ServiceNowAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        table_type = Field(str, "Table Type")
        class_name = Field(str, "Class Name")

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _connect_client(self, client_config):
        try:
            connection = ServiceNowConnection(
                domain=client_config["domain"], verify_ssl=client_config["verify_ssl"],
                url_base_prefix="api/now/", number_of_offsets=int(self.config["DEFAULT"]["number_of_offsets"]),
                offset_size=int(self.config["DEFAULT"]["offset_size"]), username=client_config["username"],
                password=client_config["password"], https_proxy=client_config.get("https_proxy"),
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
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
        Get all devices from a specific ServiceNow domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a ServiceNow connection

        :return: A json with all the attributes returned from the ServiceNow Server
        """
        try:
            client_data.connect()
            yield from client_data.get_device_list()
        finally:
            client_data.close()

    def _clients_schema(self):
        """
        The schema ServiceNowAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "domain",
                    "title": "ServiceNow Domain",
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
                "verify_ssl"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for table_devices_data in devices_raw_data:
            for device_raw in table_devices_data[DEVICES_KEY]:
                try:
                    device = self._new_device_adapter()
                    device.id = str(device_raw.get("sys_id", ""))
                    if device.id == "":
                        continue
                    device.table_type = table_devices_data[DEVICE_TYPE_NAME_KEY]
                    device.name = device_raw.get("name")
                    device.class_name = device_raw.get("sys_class_name")
                    ip_address = device_raw.get("ip_address", "")
                    mac_address = device_raw.get("mac_address", "")
                    if mac_address is not "" or ip_address is not "":
                        device.add_nic(mac_address, ip_address.split(","))
                    device.figure_os(
                        device_raw.get("os", "") + " " + device_raw.get("os_address_width", "") + " " + device_raw.get(
                            "os_domain", "") +
                        " " + device_raw.get("os_service_pack", "") + " " + device_raw.get("os_version", ""))
                    device.device_model = device_raw.get("model_number")
                    device.device_serial = device_raw.get("serial_number")
                    ram_mb = device_raw.get("ram", "")
                    if ram_mb != "" and ram_mb != "-1" and ram_mb != -1:
                        device.total_physical_memory = int(ram_mb) / 1024.0
                    host_name = device_raw.get("host_name", "")
                    if host_name != "":
                        device.hostname = host_name
                    device.description = device_raw.get("short_description")
                    device.set_raw(device_raw)
                    yield device
                except Exception:
                    logger.exception("Problem with fetching ServiceNow Device")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
