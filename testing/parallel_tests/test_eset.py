import pytest
from services.adapters.eset_service import EsetService, eset_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_eset_credentials import *


class TestEsetAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return EsetService()

    @property
    def adapter_name(self):
        return 'eset_adapter'

    @property
    def some_client_id(self):
        return ':'.join([eset_details['host'], eset_details['port']])

    @property
    def some_client_details(self):
        return eset_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
