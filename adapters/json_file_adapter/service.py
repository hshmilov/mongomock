from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter

import json

from axonius.utils.files import get_local_config_file
from typing import List

DATA = 'data'


class JsonFileAdapter(AdapterBase):
    @classmethod
    def adapter_properties(cls) -> List[AdapterProperty]:
        return []

    __additional_fields = []

    @staticmethod
    def additional():
        return JsonFileAdapter.__additional_fields

    @staticmethod
    def set_additional(fields):
        JsonFileAdapter.__additional_fields = fields

    class MyDeviceAdapter(DeviceAdapter):

        @classmethod
        def get_fields_info(cls):
            base = super().get_fields_info().copy()
            base['items'].extend(JsonFileAdapter.additional())
            return base

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _connect_client(self, client_config):
        return client_config

    def _query_devices_by_client(self, client_name, client_data):
        as_string = bytes(client_data[DATA]).decode()
        return json.loads(as_string)

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": DATA,
                    "title": "Connection details",
                    "description": "Connection details",
                    "type": "array",
                    "format": "bytes",
                    "items": {
                        "type": "integer",
                        "default": 0,
                    }
                }
            ],
            "required": [
                DATA,
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        self._fields_set = set(devices_raw_data['fields'])
        self._raw_fields_set = set(devices_raw_data['raw_fields'])
        self.set_additional(devices_raw_data['additional_schema'])

        for device_raw in devices_raw_data['devices']:
            device = self._new_device_adapter()
            device._dict = device_raw
            yield device

    def _get_client_id(self, client_config):
        return "1"
