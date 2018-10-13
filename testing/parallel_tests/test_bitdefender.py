# we need fixture so ignore unused
# pylint: disable=W0611
import pytest

from services.adapters.bitdefender_service import (BitdefenderService,
                                                   bitdefender_fixture)
from test_credentials.test_bitdefender_credentials import (SOME_DEVICE_ID,
                                                           client_details)
from test_helpers.adapter_test_base import AdapterTestBase


class TestBitdefenderAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return BitdefenderService()

    @property
    def some_client_id(self):
        return client_details['domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_user_id(self):
        raise NotImplementedError

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip('AX-2238')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('No reachability test')
    def test_check_reachability(self):
        pass

    @pytest.mark.skip('No reachability test')
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip('No reachability test')
    def test_removing_adapter_creds_with_users(self):
        pass
