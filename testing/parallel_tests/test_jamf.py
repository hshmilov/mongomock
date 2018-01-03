from services.adapters.jamf_service import JamfService, jamf_fixture
from test_helpers.adapter_test_base import AdapterTestBase


# this is our aws SEP manager and its name is Windows-Sep-Server
client_details = {
    "Jamf_Domain": "https://axoniusdev.jamfcloud.com",
    "username": "axonius",
    "password": "wBV8LgOP4uHrnKiq3VMQ"
}

SOME_DEVICE_ID = 'ea47e7b3c04f6560f2ac739bb0b0f9df83355ebc'  # our iPad


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
