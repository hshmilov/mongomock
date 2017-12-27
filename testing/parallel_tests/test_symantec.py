import pytest
from services.adapters.symantec_service import SymantecService, symantec_fixture
from test_helpers.adapter_test_base import AdapterTestBase

# this is our aws SEP manager and its name is Windows-Sep-Server
client_details = {
    "Symantec_Domain": "10.0.2.171",
    "username": "admin",
    "password": "7ldUJKtYG8oe1243fds"
}

SOME_DEVICE_ID = 'DEDB73460A0002AB70C44D039ADC2249'  # our ESXmachine windows8


class TestSymantecAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return SymantecService()

    @property
    def adapter_name(self):
        return 'symantec_adapter'

    @property
    def some_client_id(self):
        return client_details['Symantec_Domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip
    def test_fetch_devices(self):
        pass
