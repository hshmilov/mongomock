import pytest
# pylint: disable=unused-import
from services.adapters.censys_service import CensysService, censys_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_censys_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from censys_adapter.client_id import get_client_id


class TestCensysAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return CensysService()

    @property
    def adapter_name(self):
        return 'censys_adapter'

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

    @pytest.mark.skip('Skip because of 250 calls/month Censys API limit')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('Skip because of 250 calls/month Censys API limit')
    def test_check_reachability(self):
        pass
