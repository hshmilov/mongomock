import pytest
from services.adapters.service_now_service import ServiceNowService, service_now_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_service_now_credentials import *


class TestServiceNowAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return ServiceNowService()

    @property
    def some_client_id(self):
        return client_details['domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("not working, ask Ofri Shur for more details")
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('no server')
    def test_check_reachability(self):
        pass
