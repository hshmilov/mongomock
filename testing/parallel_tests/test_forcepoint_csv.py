import pytest
from services.adapters.forcepoint_csv_service import forcepoint_csv_fixture, ForcepointCsvService
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_forcepoint_csv_credentials import *


class TestForcepointCsvAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return ForcepointCsvService()

    @property
    def some_client_id(self):
        return client_details['user_id']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("No reachability test")
    def test_check_reachability(self):
        pass
