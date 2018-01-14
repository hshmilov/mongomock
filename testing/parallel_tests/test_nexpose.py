import pytest
from services.adapters.nexpose_service import NexposeService, nexpose_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_nexpose_credentials import *


class TestNexposeAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return NexposeService()

    @property
    def adapter_name(self):
        return 'nexpose_adapter'

    @property
    def some_client_id(self):
        return nexpose_details['host']

    @property
    def some_client_details(self):
        return nexpose_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    def test_fetch_devices(self):
        super().test_fetch_devices()
        devices_as_dict = self.adapter_service.devices()

        # check the device is read by adapter
        devices_list = devices_as_dict[self.some_client_id]['parsed']
        nexpose_device = list(filter(lambda device: device['hostname'] == FETCHED_DEVICE_EXAMPLE['hostname'],
                                     devices_list))
        assert nexpose_device[0]['raw']['mac_address'] == FETCHED_DEVICE_EXAMPLE['raw']['mac_address']
