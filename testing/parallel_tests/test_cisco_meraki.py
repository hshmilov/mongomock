from services.adapters.cisco_meraki_service import CiscoMerakiService, cisco_meraki_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_cisco_meraki_credentials import *


class TestCiscoMerakiAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return CiscoMerakiService()

    @property
    def some_client_id(self):
        return client_details['CiscoMeraki_Domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
