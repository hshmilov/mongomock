# pylint: disable=unused-import
import pytest

from services.adapters.keycloak_service import KeycloakService, keycloak_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_keycloak_credentials import CLIENT_DETAILS, SOME_DEVICE_ID


class TestKeycloakAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return KeycloakService()

    @property
    def adapter_name(self):
        return 'keycloak_adapter'

    @property
    def some_client_id(self):
        return f'Keycloak_{CLIENT_DETAILS["domain"]}_{CLIENT_DETAILS["username"]}'

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @property
    def some_user_id(self):
        raise SOME_DEVICE_ID

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

    @pytest.mark.skip('no server')
    def test_fetch_users(self):
        pass
