import pytest

# pylint: disable=unused-import
from services.adapters.symantec_cloud_workload_service import SymantecCloudWorkloadService, \
    symantec_cloud_workload_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_symantec_cloud_workload_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from symantec_cloud_workload_adapter.client_id import get_client_id


class TestSymantecCloudWorkloadAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return SymantecCloudWorkloadService()

    @property
    def adapter_name(self):
        return 'symantec_cloud_workload_adapter'

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
        raise NotImplementedError()

    @pytest.mark.skip('no server')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('no server')
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip('no server')
    def test_removing_adapter_creds_with_users(self):
        pass

    @pytest.mark.skip('no server')
    def test_check_reachability(self):
        pass
