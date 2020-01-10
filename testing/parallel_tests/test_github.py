# pylint: disable=unused-import
import pytest

from services.adapters.github_service import GithubService, github_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_github_credentials import CLIENT_DETAILS, SOME_USER_ID
from github_adapter.client_id import get_client_id


class TestGithubAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return GithubService()

    @property
    def adapter_name(self):
        return 'github_adapter'

    @property
    def some_client_id(self):
        return get_client_id(CLIENT_DETAILS)

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_user_id(self):
        return SOME_USER_ID

    @property
    def some_device_id(self):
        raise NotImplementedError()

    @pytest.mark.skip('No creds')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('No creds')
    def test_fetch_users(self):
        pass

    @pytest.mark.skip('No creds')
    def test_check_reachability(self):
        pass

    @pytest.mark.skip('No creds')
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip('No creds')
    def test_removing_adapter_creds_with_users(self):
        pass
