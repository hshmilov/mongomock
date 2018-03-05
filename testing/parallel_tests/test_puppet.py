import pytest
from services.adapters.puppet_service import PuppetService, puppet_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_puppet_credentials import *


class TestPuppetAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return PuppetService()

    @property
    def adapter_name(self):
        return 'puppet_adapter'

    @property
    def some_client_id(self):
        return client_details['puppet_server_name']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("Test took 8 minutes. Need to fix it")
    def test_fetch_devices(self):
        pass
