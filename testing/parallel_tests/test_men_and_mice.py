import pytest
# pylint: disable=unused-import
from services.adapters.men_and_mice_service import MenAndMiceService, men_and_mice_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_men_and_mice_credentials import (
    CLIENT_DETAILS,
    SOME_DEVICE_ID,
    SOME_USER_ID
)
from men_and_mice_adapter.client_id import get_client_id


class TestMenAndMiceAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return MenAndMiceService()

    @property
    def adapter_name(self):
        return 'men_and_mice_adapter'

    @property
    def some_client_id(self):
        # return get_client_id(CLIENT_DETAILS)
        return None

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @property
    def some_user_id(self):
        return SOME_USER_ID

    @pytest.mark.skip('AX-6171')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('AX-6171')
    def test_fetch_users(self):
        pass

    @pytest.mark.skip('No creds')
    def test_check_reachability(self):
        pass
