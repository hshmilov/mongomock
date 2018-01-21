import pytest
from services.adapters.cisco_service import CiscoService, cisco_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_cisco_credentials import cisco_creds


class TestCiscoAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return CiscoService()

    @property
    def adapter_name(self):
        return 'cisco_adapter'

    @property
    def some_client_id(self):
        return cisco_creds['host']

    @property
    def some_client_details(self):
        return cisco_creds

    @property
    def some_device_id(self):
        return cisco_creds['host']

    def test_fetch_devices(self):
        pass
