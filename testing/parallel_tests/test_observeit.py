import pytest
from services.adapters.observeit_service import observeit_fixture, ObserveitService
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_observeit_credentials import *


class TestObserveitAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return ObserveitService()

    @property
    def some_client_id(self):
        return client_details['server']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("test is broken - ofri should fix - AX-1840.")
    def test_fetch_devices(self):
        pass
