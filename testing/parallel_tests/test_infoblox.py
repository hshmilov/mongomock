import pytest

from services.adapters.infoblox_service import InfobloxService, infoblox_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_infoblox_credentials import *


class TestInfobloxAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return InfobloxService()

    @property
    def some_client_id(self):
        return client_details['domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    def test_fetch_devices(self):
        # The trail was set on the 28.9.18, it should not work in 2 months, or 3 months.
        super().test_fetch_devices()

    @pytest.mark.skip("No reachability test")
    def test_check_reachability(self):
        pass
