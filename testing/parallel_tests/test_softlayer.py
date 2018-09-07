import pytest
from services.adapters.softlayer_service import SoftlayerService, softlayer_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_softlayer_credentials import *


class TestSoftlayerAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return SoftlayerService()

    @property
    def some_client_id(self):
        return client_details['username']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("Skipped by Avidor")
    def test_fetch_devices(self):
        pass

    def test_check_reachability(self):
        assert self.adapter_service.is_client_reachable(self.some_client_details)
