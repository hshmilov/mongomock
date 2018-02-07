from fortigate_client import FortigateClient
import fortigate_consts
import datetime

from axonius.adapter_base import AdapterBase
from axonius.parsing_utils import format_mac
from axonius.device import Device
import axonius.adapter_exceptions


class FortigateAdapter(AdapterBase):
    """
    Connects axonius to Fortigate devices
    """

    class MyDevice(Device):
        pass

    def __init__(self, **kwargs):
        """Class initialization.

        Check AdapterBase documentation for additional params and exception details.

        """
        # Initialize the base plugin (will initialize http server)
        super().__init__(**kwargs)

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": fortigate_consts.FORTIGATE_HOST,
                    "title": "Host Name",
                    "type": "string"
                },
                {
                    "name": fortigate_consts.FORTIGATE_PORT,
                    "title": "Port",
                    "type": "integer"
                },
                {
                    "name": fortigate_consts.USER,  # The user needs System Configuration Read Privileges.
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": fortigate_consts.PASSWORD,
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": fortigate_consts.VDOM,
                    "title": "Virtual Domain",
                    "type": "string"
                },
                {
                    "name": fortigate_consts.DHCP_LEASE_TIME,
                    "title": "DHCP Lease Time (In Seconds)",
                    "type": "integer"
                },
                {  # if false, it will allow for invalid SSL certificates (but still uses HTTPS)
                    "name": fortigate_consts.VERIFY_SSL,
                    "title": "Verify SSL",
                    "type": "bool"
                }
            ],
            "required": [
                fortigate_consts.USER,
                fortigate_consts.PASSWORD,
                fortigate_consts.FORTIGATE_HOST,
            ],
            "type": "array"
        }

    def _parse_raw_data(self, raw_data):
        dhcp_lease_time = raw_data.get(fortigate_consts.DHCP_LEASE_TIME, fortigate_consts.DEFAULT_DHCP_LEASE_TIME)
        for currnet_interface in raw_data.get('results', []):
            for raw_device in currnet_interface.get('list', []):
                device = self._new_device()
                device.hostname = raw_device.get('hostname', '')
                mac_address = format_mac(raw_device.get('mac', ''))
                device.id = mac_address
                device.add_nic(mac_address, [raw_device.get("ip")] if raw_device.get("ip") else [], self.logger)
                device.scanner = True

                last_seen = raw_device.get('expire_time')
                # The DHCP lease time is kept in seconds and by getting the dhcp lease expiry - lease time
                # would let us know when the dhcp lease occurred which we would use as last_seen.
                device.last_seen = datetime.datetime.fromtimestamp(
                    last_seen) - datetime.timedelta(seconds=dhcp_lease_time)

                device.set_raw(raw_device)

                yield device

    def _query_devices_by_client(self, client_name, client_data):
        try:
            assert isinstance(client_data, FortigateClient)
            return client_data.get_all_devices()
        except Exception as err:
            self.logger.exception(f'Failed to get all the devices from the client: {client_data}')
            # TODO: Change to GetDevicesError after nexpose refactor is merged.
            raise axonius.adapter_exceptions.AdapterException(
                f'Failed to get all the devices from the client: {client_data}')

    def _get_client_id(self, client_config):
        return f"{client_config[fortigate_consts.FORTIGATE_HOST]}:{client_config.get(fortigate_consts.FORTIGATE_PORT, fortigate_consts.DEFAULT_FORTIGATE_PORT)}"

    def _connect_client(self, client_config):
        try:
            return FortigateClient(self.logger, **client_config)
        except Exception as err:
            self.logger.exception(f'Failed to connect to Fortigate client using this config {client_config}')
            raise axonius.adapter_exceptions.ClientConnectionException(
                f'Failed to connect to Fortigate client using this config {client_config}')
