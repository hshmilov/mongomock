import pytest
# pylint: disable=unused-import
from services.adapters.zscaler_service import ZscalerService, zscaler_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_zscaler_credentials import CLIENT_DETAILS, SOME_DEVICE_ID, OLD_CLIENT_DETAILS
from zscaler_adapter.client_id import get_client_id


class TestZscalerAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return ZscalerService()

    @property
    def adapter_name(self):
        return 'zscaler_adapter'

    @property
    def some_client_id(self):
        return get_client_id(OLD_CLIENT_DETAILS)

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
