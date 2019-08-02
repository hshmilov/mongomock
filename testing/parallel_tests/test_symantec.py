import pytest
from flaky import flaky
from services.adapters.symantec_service import SymantecService, symantec_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_symantec_credentials import *


class TestSymantecAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return SymantecService()

    @property
    def some_client_id(self):
        return client_details['domain'] + '_' + client_details['username'] + '_' +\
            (client_details.get('username_domain') or '')

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip('AX-2163')
    def test_fetch_devices(self):
        pass
