import pytest

# pylint: disable=unused-import
from services.adapters.thycotic_service import ThycoticService, thycotic_fixture
from test_credentials.test_thycotic_vault_credentials import THYCOTIC_SECRET_SEREVER, THYCOTIC_USER_ID
from test_helpers.adapter_test_base import AdapterTestBase
from thycotic_adapter.client_id import get_client_id


class TestThycoticAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return ThycoticService()

    @property
    def adapter_name(self):
        return 'thycotic_adapter'

    @property
    def some_client_id(self):
        return get_client_id(THYCOTIC_SECRET_SEREVER)

    @property
    def some_client_details(self):
        return THYCOTIC_SECRET_SEREVER

    @property
    def some_device_id(self):
        raise NotImplementedError()

    @property
    def some_user_id(self):
        return THYCOTIC_USER_ID

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
