import pytest
from services.adapters.hyper_v_service import HyperVService, hyper_v_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_hyper_v_credentials import *


class TestAwsAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return HyperVService()

    @property
    def some_client_id(self):
        return client_details['host']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
