import pytest
from services.adapters.tanium_service import TaniumService, tanium_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_tanium_credentials import *


class TestTaniumAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return TaniumService()

    @property
    def some_client_id(self):
        return CLIENT_DETAILS['domain']

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("No test environment.")
    def test_fetch_devices(self):
        pass
