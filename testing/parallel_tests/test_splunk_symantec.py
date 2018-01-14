import pytest
from services.axonius_service import get_service
from services.adapters.splunk_symantec_service import SplunkSymantecService, splunk_symantec_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_splunk_symantec_credentials import *


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

    def test_fetch_devices(self):
        self.adapter_service.add_client(self.some_client_details)
        devices_as_dict = self.adapter_service.devices()
        # splunk symantec returns only online devices - both in raw and parsed devices
        assert len(devices_as_dict[self.some_client_id]['raw']) == 0
        assert len(devices_as_dict[self.some_client_id]['parsed']) == 0

        # we test that the cache database of splunk symantec has devices from all times
        axonius_service = get_service()
        fetched_machine = axonius_service.db.client[self.adapter_service.unique_name]['symantec_queries']\
            .find({'name': FETCHED_DEVICE_EXAMPLE['hostname']}).next()
        assert fetched_machine['host']['os'] == FETCHED_DEVICE_EXAMPLE['raw']['host']['os']
        assert fetched_machine['host']['network'][2]['mac'] == FETCHED_DEVICE_EXAMPLE[
            'raw']['host']['network'][2]['mac']
