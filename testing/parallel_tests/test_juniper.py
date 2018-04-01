import pytest

from services.adapters.juniper_service import JuniperService, juniper_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_juniper_credentials import client_details, SOME_DEVICE_ID


class TestJuniperAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return JuniperService()

    @property
    def adapter_name(self):
        return 'juniper_adapter'

    @property
    def some_client_id(self):
        return f"{client_details['username']}@{client_details['host']}"

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("No test environment.")
    def test_fetch_devices(self):
        pass
