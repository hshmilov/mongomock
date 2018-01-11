import pytest
from services.adapters.nexpose_service import NexposeService, nexpose_fixture
from test_helpers.adapter_test_base import AdapterTestBase


nexpose_details = {
    "host": "192.168.20.10",
    "port": "3780",
    "username": "nxadmin",
    "password": "IAmDeanSysMan1@",
    "verify_ssl": False
}


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
        return '10'

    def test_fetch_devices(self):
        super().test_fetch_devices()
        devices_as_dict = self.adapter_service.devices()

        # check the device is read by adapter
        devices_list = devices_as_dict[self.some_client_id]['parsed']
        nexpose_device = list(filter(lambda device: device['hostname'] == 'nexpose', devices_list))
        assert nexpose_device[0]['raw']['mac_address'] == '00:50:56:91:00:66'
