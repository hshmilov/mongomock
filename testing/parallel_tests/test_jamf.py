import pytest

from axonius.device import NETWORK_INTERFACES_FIELD, OS_FIELD
from services.adapters.jamf_service import JamfService, jamf_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_jamf_credentials import *


class TestJamfAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return JamfService()

    @property
    def adapter_name(self):
        return 'jamf_adapter'

    @property
    def some_client_id(self):
        return client_details['Jamf_Domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip
    def test_fetch_devices(self):
        # We remove the search and re-create it every time - two parallel tests could
        # interrupt each other so for stability it's skipped
        pass
