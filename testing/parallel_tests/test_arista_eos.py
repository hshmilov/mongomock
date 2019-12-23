import pytest
# pylint: disable=unused-import
# pylint: disable=E0401
from services.adapters.arista_eos_service import AristaEosService, arista_eos_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_arista_eos_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from arista_eos_adapter.client_id import get_client_id


class TestAristaEosAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return AristaEosService()

    @property
    def adapter_name(self):
        return 'arista_eos_adapter'

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

    @pytest.mark.skip('no test envierment')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('no test envierment')
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip('no test envierment')
    def test_removing_adapter_creds_with_users(self):
        pass

    @pytest.mark.skip('no test envierment')
    def test_check_reachability(self):
        pass
