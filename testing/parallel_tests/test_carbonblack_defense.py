from services.adapters.carbonblack_defense_service import carbonblack_defense_fixture, CarbonblackDefenseService
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_carbonblack_defense_credentials import *
import pytest


class TestCarbonblackDefenseAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return CarbonblackDefenseService()

    @property
    def some_client_id(self):
        return client_details['domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("Slow")
    def test_check_reachability(self):
        pass
