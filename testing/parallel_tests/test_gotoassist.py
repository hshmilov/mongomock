import pytest

from services.adapters.gotoassist_service import GotoassistService, gotoassist_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_gotoassist_credentials import *


class TestGotoassistAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return GotoassistService()

    @property
    def adapter_name(self):
        return 'gotoassist_adapter'

    @property
    def some_client_id(self):
        return client_details['user_name']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
