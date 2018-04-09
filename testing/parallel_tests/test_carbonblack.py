from services.adapters.carbonblack_service import carbonblack_fixture, CarbonblackService
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_carbonblack_credentials import *
import pytest


class TestCarbonblackAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return CarbonblackService()

    @property
    def adapter_name(self):
        return 'carbonblack_adapter'

    @property
    def some_client_id(self):
        return client_details['Carbonblack_Domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
