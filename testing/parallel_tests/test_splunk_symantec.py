import pytest
from services.adapters.splunk_symantec_service import SplunkSymantecService, splunk_symanctec_fixture

from test_helpers.adapter_test_base import AdapterTestBase

splunk_details = {
    "host": "10.0.2.4",
    "port": "8089",
    "username": "admin",
    "password": "IAmDeanSysMan1@",
}


class TestSplunkSymantecAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return SplunkSymantecService()

    @property
    def adapter_name(self):
        return 'splunk_symantec_adapter'

    @property
    def some_client_id(self):
        return '{0}:{1}'.format(splunk_details['host'], splunk_details['port'])

    @property
    def some_client_details(self):
        return splunk_details

    @property
    def some_device_id(self):
        return 1

    def test_fetch_devices(self):
        self.adapter_service.add_client(self.some_client_details)
        devices_as_dict = self.adapter_service.devices()
        assert len(devices_as_dict) > 0

        # check the device is read by adapter
        devices_list = devices_as_dict[self.some_client_id]['raw']
        ofri_machine = list(filter(lambda device: device['name'] == 'Axonius-Ofri', devices_list))
        assert len(ofri_machine) == 1
        assert ofri_machine[0]['os'] == 'Windows 10 (10.0.16299 ) '
        assert ofri_machine[0]['network'][2]['mac'] == 'f8-59-71-94-58-09'
