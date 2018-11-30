import pytest

# pylint: disable=unused-import
from services.adapters.oracle_cloud_service import OracleCloudService, oracle_cloud_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_oracle_cloud_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from oracle_cloud_adapter.client_id import get_client_id


class TestOracleCloudAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return OracleCloudService()

    @property
    def adapter_name(self):
        return 'oracle_cloud_adapter'

    @property
    def some_client_id(self):
        return get_client_id(CLIENT_DETAILS)

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

    @pytest.mark.skip('No need in this')
    def test_check_reachability(self):
        pass
