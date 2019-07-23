import pytest
# pylint: disable=unused-import,line-too-long
from services.adapters.cisco_firepower_management_center_service import CiscoFirepowerManagementCenterService, cisco_firepower_management_center_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_cisco_firepower_management_center_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from cisco_firepower_management_center_adapter.client_id import get_client_id


class TestCiscoFirepowerManagementCenterAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return CiscoFirepowerManagementCenterService()

    @property
    def adapter_name(self):
        return 'cisco_firepower_management_center_adapter'

    @property
    def some_client_id(self):
        return get_client_id(CLIENT_DETAILS)

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @property
    def some_user_id(self):
        raise NotImplementedError()

    @pytest.mark.skip('no server')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('no server')
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip('no server')
    def test_removing_adapter_creds_with_users(self):
        pass

    @pytest.mark.skip('no server')
    def test_check_reachability(self):
        pass
