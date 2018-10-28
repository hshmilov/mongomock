from services.adapters.tenable_security_center_service import TenableSecurityCenterService, tenable_security_center_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_tenable_security_center_credentials import *
from tenable_security_center_adapter.service import TenableSecurityCenterAdapter
import pytest


class TestTenableSecurityCenterAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return TenableSecurityCenterService()

    @property
    def some_client_id(self):
        return client_details['url']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

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
        teanable_sc_device = list(filter(lambda device: device.get('hostname', '').lower() == FETCHED_DEVICE_EXAMPLE['hostname'].lower(),
                                         devices_list))
        assert teanable_sc_device[0]['raw']['dnsName'] == HOST_NAME_EXAMLPE
