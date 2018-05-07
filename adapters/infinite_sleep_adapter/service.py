
from time import sleep

from axonius.adapter_base import AdapterBase
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file


class InfiniteSleepAdapter(AdapterBase):
    """
    An adapter for an infinite sleep while fetching devices to test research phase stop
    """

    class MyDeviceAdapter(DeviceAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _query_devices_by_client(self, client_name, client_data):
        while True:
            sleep(1)
        return []

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": "device_count",
                    "title": "Device Count",
                    "type": "number"
                },
                {
                    "name": "name",
                    "title": "Server Name",
                    "type": "string"
                }
            ],
            "required": [
                "name"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        return

    def _get_client_id(self, client_config):
        return client_config['name']

    def _connect_client(self, client_config):
        return client_config['name']

    @classmethod
    def adapter_properties(cls):
        return []
