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
        super().test_fetch_devices()

        devices_as_dict = self.adapter_service.devices()

        # check the device is read by adapter
        devices_list = devices_as_dict[self.some_client_id]['parsed']
        jamf_device = list(filter(lambda device: device.get('hostname', '') ==
                                  FETCHED_DEVICE_EXAMPLE['hostname'], devices_list))
        assert jamf_device[0][OS_FIELD] == FETCHED_DEVICE_EXAMPLE[OS_FIELD]
        assert jamf_device[0][NETWORK_INTERFACES_FIELD] == FETCHED_DEVICE_EXAMPLE[NETWORK_INTERFACES_FIELD]
