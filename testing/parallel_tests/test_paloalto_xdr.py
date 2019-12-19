import pytest

# pylint: disable=unused-import
from services.adapters.paloalto_xdr_service import PaloaltoXdrService, paloalto_xdr_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_paloalto_xdr_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from paloalto_xdr_adapter.client_id import get_client_id


class TestPaloaltoXdrAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return PaloaltoXdrService()

    @property
    def adapter_name(self):
        return 'paloalto_xdr_adapter'

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
