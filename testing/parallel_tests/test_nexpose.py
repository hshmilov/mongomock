import pytest
from flaky import flaky
from services.adapters.nexpose_service import NexposeService, nexpose_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_nexpose_credentials import client_details, SOME_DEVICE_ID, FETCHED_DEVICE_EXAMPLE


class TestNexposeAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return NexposeService()

    @property
    def some_client_id(self):
        return client_details['host']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @flaky(max_runs=2)
    def test_fetch_devices(self):
        """
        test fetch devices is different because no permanent ID on scanners.
        """
        self.adapter_service.add_client(self.some_client_details)

        self.axonius_system.aggregator.query_devices(
            adapter_id=self.adapter_service.unique_name)  # send trigger to agg to refresh devices
        devices_as_dict = self.adapter_service.devices()

        assert self.some_client_id in devices_as_dict
        devices_as_dict = self.adapter_service.devices()

        # check the device is read by adapter
        devices_list = devices_as_dict[self.some_client_id]['parsed']
        nexpose_device = list(filter(lambda device: device.get('hostname', '').upper() == FETCHED_DEVICE_EXAMPLE['hostname'].upper(),
                                     devices_list))
        assert nexpose_device[0]['raw']['mac'] == FETCHED_DEVICE_EXAMPLE['raw']['mac']
