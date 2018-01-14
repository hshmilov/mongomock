from services.adapters.sentinelone_service import SentinelOneService, sentinelone_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_sentinelone_credentials import *


class TestSentinelOneAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return SentinelOneService()

    @property
    def adapter_name(self):
        return 'sentinelone_adapter'

    @property
    def some_client_id(self):
        return client_details['SentinelOne_Domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
