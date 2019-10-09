# pylint: disable=unused-import
import pytest

from services.adapters.skybox_service import SkyboxService, skybox_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_skybox_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from skybox_adapter.client_id import get_client_id


class TestSkyboxAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return SkyboxService()

    @property
    def adapter_name(self):
        return 'skybox_adapter'

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

    @pytest.mark.skip('no test env')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('no test env')
    def test_check_reachability(self):
        pass

    @pytest.mark.skip('no test env')
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip('no test env')
    def test_removing_adapter_creds_with_users(self):
        pass
