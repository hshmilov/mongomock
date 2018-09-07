import pytest

from junos_adapter.client_id import get_client_id
from services.adapters.junos_service import JunosService, junos_fixture
from test_credentials.test_junos_credentials import *
from test_helpers.adapter_test_base import AdapterTestBase


class TestJunosAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return JunosService()

    @property
    def some_client_id(self):
        return get_client_id(client_details)

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip('AX-2008')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip("No reachability test")
    def test_check_reachability(self):
        pass
