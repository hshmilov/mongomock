import pytest
# pylint: disable=unused-import
from services.adapters.saltstack_enterprise_service import SaltstackEnterpriseService, saltstack_enterprise_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_saltstack_enterprise_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from saltstack_enterprise_adapter.client_id import get_client_id


class TestSaltstackEnterpriseAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return SaltstackEnterpriseService()

    @property
    def adapter_name(self):
        return 'saltstack_enterprise_adapter'

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

    @pytest.mark.skip('Not working')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('Not working')
    def test_check_reachability(self):
        pass
