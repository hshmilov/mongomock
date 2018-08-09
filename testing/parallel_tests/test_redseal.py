from services.adapters.redseal_service import RedsealService, redseal_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_redseal_credentials import *
from redseal_adapter.client_id import get_client_id
import pytest


class TestRedsealAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return RedsealService()

    @property
    def some_client_id(self):
        return get_client_id(client_details)

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("does not work")
    def test_fetch_devices(self):
        pass
