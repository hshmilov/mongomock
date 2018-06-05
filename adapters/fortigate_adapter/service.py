import logging
logger = logging.getLogger(f"axonius.{__name__}")
import datetime

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException, GetDevicesError
from axonius.utils.parsing import format_mac
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from fortigate_adapter import consts
from fortigate_adapter.client import FortigateClient
from axonius.fields import Field


class FortigateAdapter(AdapterBase):
    """
    Connects axonius to Fortigate devices
    """

    class MyDeviceAdapter(DeviceAdapter):
        interface = Field(str, "Interface")

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": consts.FORTIGATE_HOST,
                    "title": "Host Name",
                    "type": "string"
                },
                {
                    "name": consts.FORTIGATE_PORT,
                    "title": "Port",
                    "type": "integer",
                    "format": "port"
                },
                {
                    "name": consts.USER,  # The user needs System Configuration Read Privileges.
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": consts.PASSWORD,
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": consts.VDOM,
                    "title": "Virtual Domain",
                    "type": "string"
                },
                {
                    "name": consts.DHCP_LEASE_TIME,
                    "title": "DHCP Lease Time (In Seconds)",
                    "type": "integer"
                },
                {  # if false, it will allow for invalid SSL certificates (but still uses HTTPS)
                    "name": consts.VERIFY_SSL,
                    "title": "Verify SSL",
                    "type": "bool"
                }
            ],
            "required": [
                consts.USER,
                consts.PASSWORD,
                consts.FORTIGATE_HOST,
            ],
            "type": "array"
        }

    def _parse_raw_data(self, raw_data):
        dhcp_lease_time = raw_data.get(consts.DHCP_LEASE_TIME, consts.DEFAULT_DHCP_LEASE_TIME)
        for current_interface in raw_data.get('results', []):
            for raw_device in current_interface.get('list', [current_interface]):  # If current interface does'nt hold
                # list, than its a device itself
                device = self._new_device_adapter()
                device.hostname = raw_device.get('hostname', '')
                mac_address = format_mac(raw_device.get('mac', ''))
                device.id = mac_address
                device.add_nic(mac_address, [raw_device.get("ip")] if raw_device.get("ip") else [])

                last_seen = raw_device.get('expire_time')
                # The DHCP lease time is kept in seconds and by getting the dhcp lease expiry - lease time
                # would let us know when the dhcp lease occurred which we would use as last_seen.
                device.last_seen = datetime.datetime.fromtimestamp(
                    last_seen) - datetime.timedelta(seconds=dhcp_lease_time)
                device.interface = raw_device.get('interface', '')

                device.set_raw(raw_device)

                yield device

    def _query_devices_by_client(self, client_name, client_data):
        try:
            assert isinstance(client_data, FortigateClient)
            return client_data.get_all_devices()
        except Exception as err:
            logger.exception(f'Failed to get all the devices from the client: {client_data}')
            raise GetDevicesError(f'Failed to get all the devices from the client: {client_data}')

    def _get_client_id(self, client_config):
        return f"{client_config[consts.FORTIGATE_HOST]}:{client_config.get(consts.FORTIGATE_PORT, consts.DEFAULT_FORTIGATE_PORT)}"

    def _connect_client(self, client_config):
        try:
            return FortigateClient(**client_config)
        except Exception as err:
            logger.exception(
                f'Failed to connect to Fortigate client using this config {client_config[consts.FORTIGATE_HOST]}')
            raise ClientConnectionException(
                f'Failed to connect to Fortigate client using this config {client_config[consts.FORTIGATE_HOST]}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Firewall]
