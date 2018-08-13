import logging
logger = logging.getLogger(f'axonius.{__name__}')
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.clients.rest.exception import RESTException
from infoblox_adapter.connection import InfobloxConnection


class InfobloxAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _connect_client(self, client_config):
        try:
            connection = InfobloxConnection(
                domain=client_config["domain"], verify_ssl=client_config["verify_ssl"],
                username=client_config["username"], password=client_config["password"],
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                url_base_prefix="/wapi/v2.7/")
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
        The schema InfobloxAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "domain",
                    "title": "Infoblox Domain",
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
                names = device_raw.get("names", [])
                mac_address = device_raw.get("mac_address", "")
                if names == [] and mac_address == "":
                    logger.error(f"No names or mac at : {device_raw}")
                    continue
                if device_raw.get("status", "") == "UNUSED" or "BROADCAST" in device_raw.get("types", []):
                    continue
                if mac_address != "":
                    device.id = f"mac_{mac_address}"
                else:
                    device.id = f"host_{names[0]}"
                if len(names) > 0:
                    device.hostname = names[0]
                device.add_nic(mac_address, [device_raw.get("ip_address")])
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception("Problem with fetching Infoblox Device")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
