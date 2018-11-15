import pytest
from services.adapters.splunk_service import SplunkService, splunk_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_splunk_credentials import *


class TestSplunkAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return SplunkService()

    @property
    def some_client_id(self):
        return '{0}:{1}'.format(splunk_details['host'], splunk_details['port'])

    @property
    def some_client_details(self):
        return splunk_details

    @property
    def some_device_id(self):
        return FETCHED_DEVICE_EXAMPLE['id']

    def test_fetch_devices(self):
        self.adapter_service.set_configurable_config('SplunkAdapter', 'fetch_nexpose', True)
        self.adapter_service.set_configurable_config('SplunkAdapter', 'max_log_history', 365 * 2)
        super().test_fetch_devices()
        devices_as_dict = self.adapter_service.devices()
        assert len(devices_as_dict) > 0

        # check the device is read by adapter
        devices_list = devices_as_dict[self.some_client_id]['parsed']
        nexpose_device = list(filter(lambda device: device.get('hostname', '') == FETCHED_DEVICE_EXAMPLE['hostname'],
                                     devices_list))
        assert nexpose_device[0]['raw']['mac'] == FETCHED_DEVICE_EXAMPLE['raw']['mac']
