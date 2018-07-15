import pytest

from services.adapters.oracle_vm_service import OracleVmService, oracle_vm_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_oracle_vm_credentials import *


class TestOracleVmAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return OracleVmService()

    @property
    def some_client_id(self):
        return client_details['domain']

    @property
    def some_client_details(self):
        return client_details

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
