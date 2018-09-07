import pytest
from services.adapters.cisco_amp_service import (CiscoAmpService,
                                                 cisco_amp_fixture)
from test_credentials.test_cisco_amp_credentials import (CLIENT_DETAILS,
                                                         SOME_DEVICE_ID)
from test_helpers.adapter_test_base import AdapterTestBase


class TestCiscoAmpAdapter(AdapterTestBase):

    @property
    def adapter_service(self):
        return CiscoAmpService()

    @property
    def some_client_id(self):
        return CLIENT_DETAILS['domain']

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("No test environment.")
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip("No test env")
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip("No test env")
    def test_removing_adapter_creds_with_users(self):
        pass

    @pytest.mark.skip('No reachability test')
    def test_check_reachability(self):
        pass
