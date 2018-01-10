import pytest
from services.adapters.jamf_service import JamfService, jamf_fixture
from test_helpers.adapter_test_base import AdapterTestBase

# this is our jamf pro cloud.
client_details = {
    "Jamf_Domain": "https://axoniusdev.jamfcloud.com",
    "username": "axonius",
    "password": "wBV8LgOP4uHrnKiq3VMQ"
}

# Our office Mac mini (Axonius Printer)
SOME_DEVICE_ID = '9AE9A131-6801-5659-A1AE-C9B38F1EA4C4'


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

    def test_fetch_devices(self):
        super().test_fetch_devices()

        devices_as_dict = self.adapter_service.devices()

        # check the device is read by adapter
        devices_list = devices_as_dict[self.some_client_id]['parsed']
        jamf_device = list(filter(lambda device: device['hostname'] == 'Axonius Printer', devices_list))
        assert jamf_device[0]['OS'] == {"bitness": 64, "distribution": "10.12.6", "type": "OS X"}
        assert jamf_device[0]['network_interfaces'] == [{"IP": ["141.226.237.21"], "MAC": "A8:60:B6:3C:79:FE"},
                                                        {"IP": ["192.168.11.14"], "MAC": "A8:60:B6:3C:79:FE"}]
