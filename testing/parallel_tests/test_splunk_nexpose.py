import pytest
from services.adapters.splunk_nexpose_service import SplunkNexposeService, splunk_nexpose_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_splunk_nexpose_credentials import *


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

    @pytest.mark.skip("test causes ci to fail")
    def test_fetch_devices(self):
        self.adapter_service.add_client(self.some_client_details, self.axonius_system.core.vol_conf.password_secret())
        self.axonius_system.aggregator.query_devices(adapter_id=self.adapter_service.unique_name)
        devices_as_dict = self.adapter_service.devices()
        assert len(devices_as_dict) > 0

        # check the device is read by adapter
        devices_list = devices_as_dict[self.some_client_id]['parsed']
        nexpose_device = list(filter(lambda device: device.get('hostname', '') == FETCHED_DEVICE_EXAMPLE['hostname'],
                                     devices_list))
        assert nexpose_device[0]['raw']['mac'] == FETCHED_DEVICE_EXAMPLE['raw']['mac']
