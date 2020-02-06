import pytest

# pylint: disable=unused-import
from services.adapters.json_service import JsonService, json_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_json_credentials import (CLIENT_DETAILS,
                                                    SOME_DEVICE_ID,
                                                    JSON_TEST_FIELDS)
from test_credentials.test_gui_credentials import DEFAULT_USER
from json_adapter.client_id import get_client_id

pytestmark = pytest.mark.sanity


class TestJsonAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return JsonService()

    @property
    def adapter_name(self):
        return 'json_adapter'

    @property
    def some_client_id(self):
        return get_client_id(CLIENT_DETAILS)

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip('No reachability test')
    def test_check_reachability(self):
        pass

    @property
    def some_user_id(self):
        """XXX Need to add tests for both users and devices"""
        raise NotImplementedError()

    def test_json_fields(self):
        def get_devices(adapter_name):
            res = gui_service.get_devices(params={
                'filter': '(adapters_data.json_adapter.id == ({"$exists":true,"$ne":""}))'
            }).json()
            return res

        gui_service = self.axonius_system.gui
        gui_service.login_user(DEFAULT_USER)
        assert self.adapter_service.add_client(self.some_client_details)['id'] is not None
        devices_response = get_devices(self.adapter_service.plugin_name)

        for device in devices_response:
            fields = device['adapters_data'][0]['json_adapter'].keys()
            assert all('json_' + field.replace(' ', '_') in fields for field in JSON_TEST_FIELDS)
