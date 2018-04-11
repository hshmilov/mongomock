import logging
logger = logging.getLogger(f"axonius.{__name__}")

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import AdapterException, ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from juniper_adapter import consts
from juniper_adapter.client import JuniperClient
from axonius.fields import Field


class JuniperAdapter(AdapterBase):
    """
    Connects axonius to Juniper devices
    """

    class MyDeviceAdapter(DeviceAdapter):
        interface = Field(str, 'Interface')
        device_type = Field(str, 'Device Type')
        serial = Field(str, 'Serial')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": consts.JUNIPER_HOST,
                    "title": "Host Name",
                    "type": "string"
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
                }
            ],
            "required": [
                consts.USER,
                consts.PASSWORD,
                consts.JUNIPER_HOST,
            ],
            "type": "array"
        }

    def _parse_raw_data(self, raw_data):
        for device_type, juno_device in raw_data:
            if device_type == 'arp_device':
                for arp_item in juno_device:
                    try:
                        device = self._new_device_adapter()
                        device.device_type = device_type
                        device.id = arp_item['mac_address']
                        ip_address = arp_item.get('ipAddr', None)
                        device.add_nic(arp_item['mac_address'], [ip_address]
                                       if ip_address is not None else None)
                        device.interface = arp_item.get('interface')
                        device.set_raw(arp_item)
                        yield device

                    except Exception as err:
                        logger.exception("Got bad arp item with missing data.")
            elif device_type == 'juniper_device':
                device = self._new_device_adapter()
                device.device_type = device_type
                device.id = juno_device.get('deviceId')
                device.name = juno_device.get('name')
                device.serial = juno_device.get('serial')
                device.figure_os(f"Junos OS {juno_device.get('OSVersion', '')}")
                list_of_arp_items = [current_device for current_device_type,
                                     current_device in raw_data if current_device_type == 'arp_device']
                mac_finder = [item['mac_address']
                              for item in list_of_arp_items if item['ipAddr'] == juno_device.get('ipAddr')]
                mac_address = mac_finder[0] if len(mac_finder) != 0 else None
                ip_address = arp_item.get('ipAddr', None)
                device.add_nic(mac_address, [ip_address] if ip_address is not None else None)
                device.set_raw(juno_device)
                yield device

    def _query_devices_by_client(self, client_name, client_data):
        try:
            assert isinstance(client_data, JuniperClient)
            return client_data.get_all_devices()
        except Exception as err:
            logger.exception(f'Failed to get all the devices from the client: {client_data}')
            raise AdapterException(f'Failed to get all the devices from the client: {client_data}')

    def _get_client_id(self, client_config):
        return f"{client_config[consts.USER]}@{client_config[consts.JUNIPER_HOST]}"

    def _connect_client(self, client_config):
        try:
            return JuniperClient(url=f"https://{client_config[consts.JUNIPER_HOST]}",
                                 username=client_config[consts.USER],
                                 password=client_config[consts.PASSWORD])
        except Exception as err:
            logger.exception(f'Failed to connect to Juniper provider using this config {client_config}')
            raise ClientConnectionException(f'Failed to connect to Juniper provider using this config {client_config}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
