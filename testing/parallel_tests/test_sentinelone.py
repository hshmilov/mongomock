import pytest
from services.adapters.sentinelone_service import SentineloneService, sentinelone_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_sentinelone_credentials import *


class TestSentinelOneAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return SentineloneService()

    @property
    def some_client_id(self):
        return client_details['domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip('Not working')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('Not working')
    def test_check_reachability(self):
        pass
