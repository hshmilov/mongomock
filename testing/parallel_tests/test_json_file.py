import pytest
from services.adapters.json_file_service import JsonFileService, json_file_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.json_file_credentials import client_details, SOME_DEVICE_ID

pytestmark = pytest.mark.sanity


class TestJsonFileAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return JsonFileService()

    @property
    def some_client_id(self):
        return '1'

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("No reachability test")
    def test_check_reachability(self):
        pass

    @pytest.mark.skip("Irrelevant test for this adapter")
    def test_bad_client(self):
        pass
