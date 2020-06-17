import pytest

from services.adapters.airwatch_service import AirwatchService, airwatch_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_airwatch_credentials import *


class TestAirwatchAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return AirwatchService()

    @property
    def some_client_id(self):
        return OLD_CLIENT_DETAILS['domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("Broken for some reason, to be fixed in AX-2085")
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('No creds')
    def test_check_reachability(self):
        pass
