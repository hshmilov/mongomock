from services.adapters.divvycloud_service import DivvycloudService, divvycloud_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_divvycloud_credentials import *
from divvycloud_adapter.service import DivvycloudAdapter
import pytest


class TestDivvycloudAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return DivvycloudService()

    @property
    def some_client_id(self):
        return DivvycloudAdapter._get_client_id(None, client_details)

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip('AX-2216')
    def test_fetch_devices(self):
        pass
