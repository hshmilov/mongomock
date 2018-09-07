import pytest
from flaky import flaky
from services.adapters.nessus_csv_service import NessusCsvService, nessus_csv_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_nessus_credentials import *


class TestNessusCsvAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return NessusCsvService()

    @property
    def some_client_id(self):
        return client_details['host']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @property
    def some_device_ip(self):
        return SOME_DEVICE_IP

    @pytest.mark.skip("No test environment.")
    def test_fetch_devices(self):
        self.adapter_service.add_client(self.some_client_details)
        devices_as_tuple = self.adapter_service.devices()
        devices_list = devices_as_tuple[self.some_client_id]["parsed"]

        # check the device is read by adapter
        wanted_device_list = []
        for device in devices_list:
            network_interfaces = device['network_interfaces']
            for network_interface in network_interfaces:
                ips = network_interface.get('ips', [])
                for one_ip in ips:
                    if one_ip == self.some_device_ip:
                        wanted_device_list.append(device)

        assert len(wanted_device_list) == 1, str(devices_as_tuple)

    @pytest.mark.skip("No test env")
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip("No test env")
    def test_removing_adapter_creds_with_users(self):
        pass

    @pytest.mark.skip("No reachability test")
    def test_check_reachability(self):
        pass


if __name__ == '__main__':
    import pytest
    pytest.main([__file__])
