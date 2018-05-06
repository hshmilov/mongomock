from services.adapters.carbonblack_response_service import carbonblack_response_fixture, CarbonblackResponseService
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_carbonblack_response_credentials import *
import pytest


class TestCarbonblackResponseAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return CarbonblackResponseService()

    @property
    def adapter_name(self):
        return 'carbonblack_response_adapter'

    @property
    def some_client_id(self):
        return client_details['CarbonblackResponse_Domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
