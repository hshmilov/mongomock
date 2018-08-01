# pylint: disable=unused-import
import pytest
from services.adapters.aruba_service import ArubaService, aruba_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_aruba_credentials import CLIENT_DETAILS, SOME_DEVICE_ID


class TestArubaAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return ArubaService()

    @property
    def some_client_id(self):
        return CLIENT_DETAILS['domain']

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip('No test environment.')
    def test_fetch_devices(self):
        pass
