import pytest

# pylint: disable=unused-import
from services.adapters.rancher_service import RancherService, rancher_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_rancher_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from rancher_adapter.client_id import get_client_id


class TestRancherAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return RancherService()

    @property
    def adapter_name(self):
        return 'rancher_adapter'

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

    @pytest.mark.skip('No test environment')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('No test environment')
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip('No test environment')
    def test_removing_adapter_creds_with_users(self):
        pass

    @pytest.mark.skip('No test environment')
    def test_check_reachability(self):
        pass
