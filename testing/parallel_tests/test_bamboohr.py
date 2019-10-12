import pytest
# pylint: disable=unused-import
from services.adapters.bamboohr_service import BamboohrService, bamboohr_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_bamboohr_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from bamboohr_adapter.client_id import get_client_id


class TestBamboohrAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return BamboohrService()

    @property
    def adapter_name(self):
        return 'bamboohr_adapter'

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

    @pytest.mark.skip('Skip because we do not have test creds')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('Skip because we do not have test creds')
    def test_check_reachability(self):
        pass

    # Override some others and skip them
    @pytest.mark.skip('Skip because we do not have test creds')
    def test_fetch_users(self):
        pass

    @pytest.mark.skip('Skip because we do not have test creds')
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip('Skip because we do not have test creds')
    def test_removing_adapter_creds_with_users(self):
        pass

    @pytest.mark.skip('Skip because we do not have test creds')
    def test_bad_client(self):
        pass
