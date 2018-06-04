import pytest

from services.adapters.bigfix_service import BigfixService, bigfix_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_bigfix_credentials import *


class TestBigfixAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return BigfixService()

    @property
    def some_client_id(self):
        return client_details['domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
