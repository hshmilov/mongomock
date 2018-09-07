import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_date
from blackberry_uem_adapter.connection import BlackberryUemConnection

logger = logging.getLogger(f'axonius.{__name__}')


class BlackberryUemAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        imei = Field(str, "Device IMEI")
        storage_capacity = Field(str, "Storage Capacity")
        udid = Field(str, "Device UDID")
        ownership = Field(str, "Ownership")
        hardware_name = Field(str, "Hardware Name")
        phone_number = Field(str, "Phone number")

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get("domain"))

    def _connect_client(self, client_config):
        try:

            connection = BlackberryUemConnection(domain=client_config["domain"],
                                                 verify_ssl=client_config["verify_ssl"],
                                                 https_proxy=client_config.get("https_proxy"),
                                                 username=client_config["username"], password=client_config["password"],
                                                 username_domain=client_config.get("username_domain"), port=18084,
                                                 url_base_prefix=f"{client_config['tenant_guid']}/api/v1/")
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
        Get all devices from a specific BlackberryUem domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a BlackberryUem connection

        :return: A json with all the attributes returned from the BlackberryUem Server
        """

        try:
            client_data.connect()
            yield from client_data.get_device_list()
        finally:
            client_data.close()

    def _clients_schema(self):
        """
        The schema BlackberryUemAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "domain",
                    "title": "BlackberryUem Domain",
                    "type": "string"
                },
                {
                    "name": "tenant_guid",
                    "title": "TenantGuid",
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
                    "name": "username_domain",
                    "title": "Username Domain",
                    "type": "string"
                },
                {
                    "name": "https_proxy",
                    "title": "Https Proxy",
                    "type": "string"
                }
            ],
            "required": [
                "domain",
                "username",
                "password",
                "tenant_guid",
                "verify_ssl"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device.id = device_raw.get("guid")
                if device.id is None:
                    continue
                device.udid = device_raw.get("udid")
                device.figure_os(device_raw.get("os") or "")
                device.os.distribution = device_raw.get("osVersion")
                try:
                    if device_raw.get("wifiMacAddress"):
                        device.add_nic(device_raw.get("wifiMacAddress"), None)
                except Exception:
                    logger.exception("Problem adding nic to a device")
                device.imei = device_raw.get("imei")
                device.storage_capacity = str((device_raw.get("internalStorageSize") or 0) +
                                              (device_raw.get("externalStorageSize") or 0))
                device.ownership = device_raw.get("ownership")
                device.phone_number = device_raw.get("phoneNumber")
                device.device_model = device_raw.get("hardwareModel")
                device.hardware_name = device_raw.get("hardwareName")
                device.device_serial = device_raw.get("serialNumber")
                try:
                    device.security_patch_level = parse_date(device_raw.get("securityPatchLevel"))
                except Exception:
                    logger.exception(f"Problem addinng security patch level for {device_raw}")
                try:
                    applications_raw = device_raw.get("applications", [])
                    for application_raw in applications_raw:
                        device.add_installed_software(name=application_raw.get("name"),
                                                      version=application_raw.get("version"))
                except Exception:
                    logger.exception(f"Problem adding apps to device: {device_raw}")
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception("Problem with fetching BlackberryUem Device")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
