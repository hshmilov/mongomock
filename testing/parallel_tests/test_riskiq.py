import pytest
# pylint: disable=unused-import
from services.adapters.riskiq_service import RiskiqService, riskiq_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_riskiq_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from riskiq_adapter.client_id import get_client_id


class TestRiskiqAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return RiskiqService()

    @property
    def adapter_name(self):
        return 'riskiq_adapter'

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

    @pytest.mark.skip('Not working')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('Not working')
    def test_check_reachability(self):
        pass
