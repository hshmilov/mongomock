import pytest
from flaky import flaky
from services.adapters.gotoassist_service import GotoassistService, gotoassist_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_gotoassist_credentials import *


class TestGotoassistAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return GotoassistService()

    @property
    def some_client_id(self):
        return client_details['user_name']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    def test_check_reachability(self):
        assert self.adapter_service.is_client_reachable(self.some_client_details)

    @pytest.mark.skip(
        'Skipped due to HTTP 429 Client Error: Rate limit quota'
        ' for url: https://api.getgo.com/G2A/rest/v1/companies?limit=50&offset=0')
    def test_fetch_devices(self):
        pass
