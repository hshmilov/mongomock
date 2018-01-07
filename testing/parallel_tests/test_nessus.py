from services.adapters.nessus_service import NessusService, nessus_fixture
from test_helpers.adapter_test_base import AdapterTestBase


client_details = {
    "host": "192.168.20.21",
    "username": "nessus",
    "password": "NessusRocks"
}

SOME_DEVICE_ID = "192.168.20.14"


class TestNessusAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return NessusService()

    @property
    def adapter_name(self):
        return 'nessus_adapter'

    @property
    def some_client_id(self):
        return client_details['host']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    def test_fetch_devices(self):
        super().test_fetch_devices()
        devices_as_dict = self.adapter_service.devices()

        # check the device is read by adapter
        devices_list = devices_as_dict[self.some_client_id]['parsed']
        nessus_device = list(filter(lambda device: device['id'] == SOME_DEVICE_ID, devices_list))
        assert len(nessus_device[0]['raw']['vulnerabilities']) == 52


if __name__ == '__main__':
    import pytest
    pytest.main(["parallel_tests/test_nessus.py"])
