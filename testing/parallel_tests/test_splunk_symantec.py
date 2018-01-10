import pytest
from services.axonius_service import get_service
from services.adapters.splunk_symantec_service import SplunkSymantecService, splunk_symantec_fixture
from test_helpers.adapter_test_base import AdapterTestBase


splunk_details = {
    "host": "10.0.2.4",
    "port": "8089",
    "username": "admin",
    "password": "IAmDeanSysMan1@",
    "online_hours": "24"
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
        # splunk symantec returns only online devices - both in raw and parsed devices
        assert len(devices_as_dict[self.some_client_id]['raw']) == 0
        assert len(devices_as_dict[self.some_client_id]['parsed']) == 0

        # we test that the cache database of splunk symantec has devices from all times
        axonius_service = get_service()
        ofri_machine = axonius_service.db.client[self.adapter_service.unique_name]['symantec_queries']\
            .find({'name': 'Axonius-Ofri'}).next()
        assert ofri_machine['host']['os'] == 'Windows 10 (10.0.16299 ) '
        assert ofri_machine['host']['network'][2]['mac'] == 'f8-59-71-94-58-09'
