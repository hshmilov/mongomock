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
        # return client_details['server']
        return None

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    def test_fetch_devices(self):
        pass

    @pytest.mark.skip("No reachability test")
    def test_check_reachability(self):
        pass
