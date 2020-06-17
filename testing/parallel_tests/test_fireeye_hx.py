import pytest
from services.adapters.fireeye_hx_service import FireeyeHxService, fireeye_hx_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_fireeye_hx_credentials import *


class TestFireeyeHxAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return FireeyeHxService()

    @property
    def some_client_id(self):
        # return client_details['domain']
        return None

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("No test environment.")
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip("No test env")
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip("No test env")
    def test_removing_adapter_creds_with_users(self):
        pass

    @pytest.mark.skip("No reachability test")
    def test_check_reachability(self):
        pass
