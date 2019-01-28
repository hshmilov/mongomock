import pytest

# pylint: disable=unused-import
from services.adapters.mssql_service import MssqlService, mssql_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_mssql_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from mssql_adapter.client_id import get_client_id


class TestMssqlAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return MssqlService()

    @property
    def adapter_name(self):
        return 'mssql_adapter'

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

    @pytest.mark.skip('Not now')
    def test_check_reachability(self):
        pass
