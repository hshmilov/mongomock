import pytest

# pylint: disable=unused-import
from services.adapters.haveibeenpwned_service import HaveibeenpwnedService, haveibeenpwned_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_haveibeenpwned_credentials import CLIENT_DETAILS, SOME_USER_ID
from haveibeenpwned_adapter.client_id import get_client_id


class TestHaveibeenpwnedAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return HaveibeenpwnedService()

    @property
    def adapter_name(self):
        return 'haveibeenpwned_adapter'

    @property
    def some_client_id(self):
        return get_client_id(CLIENT_DETAILS)

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        raise NotImplementedError

    @pytest.mark.skip('no server')
    def test_fetch_users(self):
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

    @property
    def some_user_id(self):
        return SOME_USER_ID

    @pytest.mark.skip('no server')
    def test_check_reachability(self):
        pass
