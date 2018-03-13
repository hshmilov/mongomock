import pytest

from services.adapters.secdo_service import SecdoService, secdo_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_secdo_credentials import *


class TestSecdoAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return SecdoService()

    @property
    def adapter_name(self):
        return 'secdo_adapter'

    @property
    def some_client_id(self):
        return client_details['Secdo_Domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    def test_fetch_devices(self):
        pass
