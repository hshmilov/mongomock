import pytest

from services.adapters.juniper_service import JuniperService, juniper_fixture
from test_helpers.adapter_test_base import AdapterTestBase


class TestJuniperAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return JuniperService()

    @property
    def adapter_name(self):
        return 'juniper_adapter'

    @property
    def some_client_id(self):
        return ''

    @property
    def some_client_details(self):
        return ''

    @property
    def some_device_id(self):
        return ''

    @pytest.mark.skip("No test environment.")
    def test_fetch_devices(self):
        pass
