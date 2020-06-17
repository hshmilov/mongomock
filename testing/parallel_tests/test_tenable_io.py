from services.adapters.tenable_io_service import TenableIoService, tenable_io_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_tenable_io_credentials import CLIENT_DETAILS, FETCHED_DEVICE_EXAMPLE, HOST_NAME_EXAMLPE
from tenable_io_adapter.client_id import get_client_id
import pytest


class TestTenableIoAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return TenableIoService()

    @property
    def some_client_id(self):
        # return get_client_id(CLIENT_DETAILS)
        return None

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        return 'xx'

    @pytest.mark.skip("Ofri should check")
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
        teanable_sc_device = list(filter(lambda device:
                                         device.get('hostname',
                                                    '').lower() == FETCHED_DEVICE_EXAMPLE['hostname'].lower(),
                                         devices_list))
        assert teanable_sc_device[0]['hostname'] == HOST_NAME_EXAMLPE

    @pytest.mark.skip('Not working')
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip('Not working')
    def test_removing_adapter_creds_with_users(self):
        pass

    @pytest.mark.skip('Slow')
    def test_check_reachability(self):
        pass
