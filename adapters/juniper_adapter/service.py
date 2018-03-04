import datetime

from axonius.adapter_base import AdapterBase
from axonius.adapter_exceptions import AdapterException, ClientConnectionException
from axonius.parsing_utils import format_mac
from axonius.devices.device import Device
from axonius.utils.files import get_local_config_file
from juniper_adapter import consts
from juniper_adapter.client import JuniperClient


class JuniperAdapter(AdapterBase):
    """
    Connects axonius to Juniper devices
    """

    class MyDevice(Device):
        pass

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

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
        pass

    def _query_devices_by_client(self, client_name, client_data):
        try:
            assert isinstance(client_data, JuniperClient)
            return client_data.get_all_devices()
        except Exception as err:
            self.logger.exception(f'Failed to get all the devices from the client: {client_data}')
            raise AdapterException(f'Failed to get all the devices from the client: {client_data}')

    def _get_client_id(self, client_config):
        return f"{client_config[consts.USER]}@{client_config[consts.JUNIPER_HOST]}"

    def _connect_client(self, client_config):
        try:
            return JuniperClient(self.logger, url=f"https://{client_config[consts.JUNIPER_HOST]}", username=client_config[consts.USER], password=client_config[consts.PASSWORD])
        except Exception as err:
            self.logger.exception(f'Failed to connect to Juniper provider using this config {client_config}')
            raise ClientConnectionException(f'Failed to connect to Juniper provider using this config {client_config}')
