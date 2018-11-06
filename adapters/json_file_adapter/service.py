from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter
from axonius.users.user_adapter import UserAdapter
from axonius.plugin_base import EntityType

import json

from axonius.utils.files import get_local_config_file
from typing import List

DEVICES_DATA = 'devices_data'
USERS_DATA = 'users_data'


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
        def get_fields_info(cls, *args, **kwargs):
            base = super().get_fields_info(*args, **kwargs).copy()
            base['items'].extend(JsonFileAdapter.additional())
            return base

    class MyUserAdapter(UserAdapter):

        @classmethod
        def get_fields_info(cls, *args, **kwargs):
            base = super().get_fields_info(*args, **kwargs).copy()
            base['items'].extend(JsonFileAdapter.additional())
            return base

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _connect_client(self, client_config):
        return client_config

    def _query_devices_by_client(self, client_name, client_data):
        return json.loads(self._grab_file_contents(client_data[DEVICES_DATA]).decode())

    def _query_users_by_client(self, key, data):
        return json.loads(self._grab_file_contents(data[USERS_DATA]).decode())

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": DEVICES_DATA,
                    "title": "Device List",
                    "description": "List of details per device to import",
                    "type": "file"
                },
                {
                    "name": USERS_DATA,
                    "title": "User List",
                    "description": "List of details per user to import",
                    "type": "file"
                }
            ],
            "required": [
                DEVICES_DATA, USERS_DATA
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

    def _parse_users_raw_data(self, raw_data):
        self._fields_set = set(raw_data['fields'])
        self._raw_fields_set = set(raw_data['raw_fields'])
        self.set_additional(raw_data['additional_schema'])

        for user_raw in raw_data['users']:
            user = self._new_user_adapter()
            user._dict = user_raw
            yield user

    def _get_client_id(self, client_config):
        return "1"

    def _test_reachability(self, client_config):
        raise NotImplementedError()
