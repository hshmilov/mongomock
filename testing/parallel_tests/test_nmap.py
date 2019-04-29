import pytest

# pylint: disable=unused-import
from services.adapters.nmap_service import NmapService, nmap_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_nmap_credentials import CLIENT_DETAILS, SOME_DEVICE_ID


class TestNmapAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return NmapService()

    @property
    def some_client_id(self):
        return CLIENT_DETAILS['user_id']

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @property
    def some_user_id(self):
        raise NotImplementedError()

    @pytest.mark.skip('Not Implemented')
    def test_check_reachability(self):
        pass

    @pytest.mark.skip('no server')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('no server')
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip('no server')
    def test_removing_adapter_creds_with_users(self):
        pass
