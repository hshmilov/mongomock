from services.adapters.junos_service import JunosService, junos_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_junos_credentials import *
from junos_adapter.service import JunosAdapter
import pytest


class TestJunosAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return JunosService()

    @property
    def some_client_id(self):
        return JunosAdapter._get_client_id(None, client_details)

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("No test environment - only local vm")
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip("No test environment - only local vm")
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip("No test environment - only local vm")
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip("No test environment - only local vm")
    def test_removing_adapter_creds_with_users(self):
        pass
