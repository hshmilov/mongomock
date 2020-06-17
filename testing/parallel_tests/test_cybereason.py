import pytest

# pylint: disable=unused-import
from services.adapters.cybereason_service import CybereasonService, cybereason_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_cybereason_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from cybereason_adapter.client_id import get_client_id


class TestCybereasonAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return CybereasonService()

    @property
    def adapter_name(self):
        return 'cybereason_adapter'

    @property
    def some_client_id(self):
        # return get_client_id(CLIENT_DETAILS)
        return None

    @property
    def some_client_detials(self):
        return CLIENT_DETAILS

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @property
    def some_user_id(self):
        raise NotImplementedError()

    @pytest.mark.skip('Not working')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('Not working')
    def test_check_reachability(self):
        pass
