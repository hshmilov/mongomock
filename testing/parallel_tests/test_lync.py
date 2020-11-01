import pytest

# pylint: disable=unused-import
from services.adapters.lync_service import LyncService, lync_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_lync_credentials import CLIENT_DETAILS, SOME_USER_ID
from lync_adapter.client_id import get_client_id


class TestLyncAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return LyncService()

    @property
    def adapter_name(self):
        return 'lync_adapter'

    @property
    def some_client_id(self):
        return get_client_id(CLIENT_DETAILS)

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        raise NotImplementedError()

    @property
    def some_user_id(self):
        return SOME_USER_ID

    @pytest.mark.skip('No test environment')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('No test environment')
    def test_fetch_users(self):
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
