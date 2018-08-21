import pytest
from flaky import flaky
from services.adapters.secdo_service import SecdoService, secdo_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_secdo_credentials import *


class TestSecdoAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return SecdoService()

    @property
    def some_client_id(self):
        return client_details['domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @flaky(max_runs=2)
    @pytest.mark.skip('AX-1828')
    def test_fetch_devices(self):
        super().test_fetch_devices()
