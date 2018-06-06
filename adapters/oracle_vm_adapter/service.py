import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from enum import Enum, auto
from oracle_vm_adapter.connection import OracleVmConnection
from axonius.clients.rest.exception import RESTException


class OracleVmDeviceType(Enum):
    """ Defines the state of device. i.e. if it is turned on or not """

    def _generate_next_value_(name, *args):
        return name

    OracleServer = auto()
    VMMachine = auto()


class OracleVmAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        device_type = Field(OracleVmDeviceType, "Device Type")
        run_state = Field(str, "Run State")
        description = Field(str, "Description")

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _connect_client(self, client_config):
        try:
            connection = OracleVmConnection(domain=client_config["domain"], verify_ssl=client_config["verify_ssl"],
                                            username=client_config["username"], password=client_config["password"],
                                            headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                                            url_base_prefix="ovm/core/wsapi/rest/")
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
        Get all devices from a specific Infoblox domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Infoblox connection

        :return: A json with all the attributes returned from the Infoblox Server
        """
        client_data.connect()
        yield from client_data.get_device_list()
        client_data.close()

    def _clients_schema(self):
        """
        The schema OracleVmAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "domain",
                    "title": "OracleVm Domain",
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

    def __create_server_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device.id = str(device_raw.get("id", {}).get("value", ""))
            if device.id == "":
                return None
            device.name = device_raw.get("name")
            device.run_state = device_raw.get("serverRunState")
            device.add_nic(None, device_raw.get("ipAddress", "").split(","))
            device.description = device_raw.get("description")
            device.bios_version = device_raw.get("biosVendor", "") + " " + device_raw.get("biosVersion", "")
            if device.bios_version == " ":
                device.bios_version = None
            ram_mb = device_raw.get("memory")
            if type(ram_mb) is int:
                device.total_physical_memory = ram_mb / 1024.0
            usuable_mb = device_raw.get("usableMemory")
            if type(usuable_mb) is int:
                device.free_physical_memory = usuable_mb / 1024.0
            device.hostname = device_raw.get("hostname")
            device.device_serial = device_raw.get("serialNumber")
            device.device_manufacturer = device_raw.get("manufacturer")
            device.device_type = OracleVmDeviceType.OracleServer
            etherent_ports_data = list(device_raw.get("etherent_ports_data", []))
            for ethernet_port_data in etherent_ports_data:
                try:
                    mac_address = ethernet_port_data.get("macAddress", "")
                    ip_addresses = ethernet_port_data.get("ipaddresses", [])
                    if type(ip_addresses) == str:
                        ip_addresses = ip_addresses.split(',')
                    if mac_address != "" or ip_addresses != []:
                        device.add_nic(mac_address, ip_addresses)
                except Exception:
                    logger.exception(f"Problem adding nic from ethernet port {ethernet_port_data}")
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f"Problem with fetching OracleVm Device {device_raw}")

    def __create_vm_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device.id = str(device_raw.get("id", {}).get("value", ""))
            if device.id == "":
                return None
            device.name = device_raw.get("name")
            device.run_state = device_raw.get("vmRunState")
            device.description = device_raw.get("description")
            if str(device.run_state).upper() == 'TEMPLATE':
                return None
            device.figure_os(device_raw.get("osType", ""))
            device.device_type = OracleVmDeviceType.VMMachine
            ram_mb = device_raw.get("currentMemory")
            if type(ram_mb) is int:
                device.total_physical_memory = ram_mb / 1024.0
            virtual_nics_data = list(device_raw.get("virtual_nics_data", []))
            for virtual_nic_data in virtual_nics_data:
                try:
                    mac_address = virtual_nic_data.get("macAddress", "")
                    ip_addresses = virtual_nic_data.get("ipAddresses", [])
                    if mac_address != "" or ip_addresses != []:
                        device.add_nic(mac_address, ip_addresses)
                except Exception:
                    logger.exception(f"Problem adding nic from virtual nic {virtual_nic_data}")
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f"Problem with fetching OracleVm Device {device_raw}")

    def _parse_raw_data(self, devices_raw_data):
        for data_type, data in devices_raw_data:
            if data_type == 'servers':
                servers = data
            elif data_type == 'vms':
                vms = data
        for device_raw in servers:
            device = self.__create_server_device(device_raw)
            if device is not None:
                yield device
        for device_raw in vms:
            device = self.__create_vm_device(device_raw)
            if device is not None:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
