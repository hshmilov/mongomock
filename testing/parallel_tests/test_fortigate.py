from services.adapters.fortigate_service import FortigateService, fortigate_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_fortigate_credentials import client_details, SOME_DEVICE_ID


class TestFortigateAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return FortigateService()

    @property
    def some_client_id(self):
        return ':'.join([client_details['host'], client_details['port']])

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
