from services.adapters.carbonblack_protection_service import carbonblack_protection_fixture, CarbonblackProtectionService
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_carbonblack_protection_credentials import *
import pytest


class TestCarbonblackProtectionAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return CarbonblackProtectionService()

    @property
    def some_client_id(self):
        return client_details['CarbonblackProtection_Domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
