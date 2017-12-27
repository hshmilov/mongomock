import pytest
from services.adapters.splunk_nexpose_service import SplunkNexposeService, splunk_nexpose_fixture

from test_helpers.adapter_test_base import AdapterTestBase


splunk_details = {
    "host": "10.0.2.4",
    "port": "8089",
    "username": "admin",
    "password": "IAmDeanSysMan1@",
}


class TestSplunkNexposeAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return SplunkNexposeService()

    @property
    def adapter_name(self):
        return 'splunk_nexpose_adapter'

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
        self.axonius_service.aggregator.query_devices()
        devices_as_dict = self.adapter_service.devices()
        assert len(devices_as_dict) > 0

        # check the device is read by adapter
        devices_list = devices_as_dict[self.some_client_id]['parsed']
        nexpose_device = list(filter(lambda device: device['hostname'] == 'nexpose', devices_list))
        assert nexpose_device[0]['raw']['mac'] == '00:50:56:91:00:66'
