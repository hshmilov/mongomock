# pylint: disable=unused-import
import pytest
from services.adapters.tanium_sq_service import TaniumSqService, tanium_sq_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_tanium_sq_credentials import CLIENT_DETAILS, SOME_DEVICE_ID


class TestTaniumSqAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return TaniumSqService()

    @property
    def adapter_name(self):
        return 'tanium_sq_adapter'

    @property
    def some_client_id(self):
        return CLIENT_DETAILS['domain']

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @property
    def some_user_id(self):
        raise NotImplementedError()

    @pytest.mark.skip('No test environment.')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('No test environment')
    def test_check_reachability(self):
        pass

    @pytest.mark.skip('No test environment')
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip('No test environment')
    def test_removing_adapter_creds_with_users(self):
        pass
