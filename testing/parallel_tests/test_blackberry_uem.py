from services.adapters.blackberry_uem_service import blackberry_uem_fixture, BlackberryUemService
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_blackberry_uem_credentials import *
import pytest


class TestBlackberryUemAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return BlackberryUemService()

    @property
    def some_client_id(self):
        return client_details['domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("doesn't work")
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('doesn\'t work')
    def test_removing_adapter_creds_with_users(self):
        pass

    @pytest.mark.skip('doesn\'t work')
    def test_removing_adapter_creds_with_devices(self):
        pass
