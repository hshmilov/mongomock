# pylint: disable=unused-import
# pylint: disable=abstract-method
import pytest
from services.adapters.dropbox_service import DropboxService, dropbox_fixture
from test_credentials.test_dropbox_credentials import (CLIENT_DETAILS,
                                                       SOME_DEVICE_ID,
                                                       SOME_MOBILE_DEVICE_ID)
from test_helpers.adapter_test_base import AdapterTestBase


class TestDropboxAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return DropboxService()

    @property
    def some_client_id(self):
        token = CLIENT_DETAILS['access_token']
        unique_id = token[:8]
        return f'dropbox_{unique_id}'

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip('Always reachable so this test is bypassed..')
    def test_check_reachability(self):
        pass

    @pytest.mark.skip('AX-2461')
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip('AX-2461')
    def test_removing_adapter_creds_with_users(self):
        pass

    @pytest.mark.skip('AX-2461')
    def test_fetch_devices(self):
        pass
