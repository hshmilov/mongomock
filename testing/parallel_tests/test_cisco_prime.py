from services.adapters.cisco_prime_service import CiscoPrimeService, cisco_prime_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_cisco_prime_credentials import *
import pytest


class TestCiscoPrimeAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return CiscoPrimeService()

    @property
    def some_client_id(self):
        return client_details['url']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip('Not working')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('Not working')
    def test_check_reachability(self):
        pass
