import pytest

# pylint: disable=unused-import
from services.adapters.knowbe4_service import Knowbe4Service, knowbe4_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_knowbe4_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from knowbe4_adapter.client_id import get_client_id


class TestKnowbe4Adapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return Knowbe4Service()

    @property
    def adapter_name(self):
        return 'knowbe4_adapter'

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
