import pytest
from flaky import flaky
from services.adapters.kaseya_service import KaseyaService, kaseya_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_kaseya_credentials import *


class TestKaseyaAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return KaseyaService()

    @property
    def some_client_id(self):
        return client_details['Kaseya_Domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
