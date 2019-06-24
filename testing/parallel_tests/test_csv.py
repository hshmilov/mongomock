import pytest

from services.adapters.csv_service import CsvService, csv_fixture
from test_credentials.test_csv_credentials import *
from test_credentials.test_gui_credentials import DEFAULT_USER
from test_helpers.adapter_test_base import AdapterTestBase

pytestmark = pytest.mark.sanity


class TestCsvAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return CsvService()

    @property
    def some_client_id(self):
        return client_details['user_id']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("No reachability test")
    def test_check_reachability(self):
        pass

    def test_csv_fields(self):
        def get_devices(adapter_name):
            res = gui_service.get_devices(params={
                'filter': '(adapters_data.csv_adapter.id == ({"$exists":true,"$ne":""}))'
            }).json()
            return res

        gui_service = self.axonius_system.gui
        gui_service.login_user(DEFAULT_USER)
        out_client_object_id = self.adapter_service.add_client(self.some_client_details)['id']
        devices_response = get_devices(self.adapter_service.plugin_name)

        for device in devices_response:
            fields = device['adapters_data'][0]['csv_adapter'].keys()
            assert all('csv_' + field.replace(' ', '_') in fields for field in CSV_FIELDS)
