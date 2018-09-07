import pytest
from flaky import flaky
from services.adapters.cisco_service import CiscoService, cisco_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_cisco_credentials import cisco_creds, SOME_DEVICE_ID


class TestCiscoAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return CiscoService()

    @property
    def some_client_id(self):
        return cisco_creds['host']

    @property
    def some_client_details(self):
        return cisco_creds

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @flaky(max_runs=2)
    def test_fetch_devices(self):
        super().test_fetch_devices()

    @pytest.mark.skip("No reachability test")
    def test_check_reachability(self):
        pass
