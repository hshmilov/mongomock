import pytest

from services.adapters.ensilo_service import EnsiloService, ensilo_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_ensilo_credentials import *


class TestEnsiloAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return EnsiloService()

    @property
    def adapter_name(self):
        return 'ensilo_adapter'

    @property
    def some_client_id(self):
        return client_details['Ensilo_Domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("Waiting to get ensilo")
    def test_fetch_devices(self):
        pass
