from services.adapters.tenable_security_center_service import TenableSecurityCenterService, tenable_security_center_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_tenable_security_center_credentials import *
from tenable_security_center_adapter.service import TenableSecurityCenterAdapter
import pytest


class TestTenableSecurityCenterAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return TenableSecurityCenterService()

    @property
    def some_client_id(self):
        return TenableSecurityCenterAdapter._get_client_id(None, client_details)

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("We don't have the actual product")
    def test_fetch_devices(self):
        pass
