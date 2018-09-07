import pytest

# we need juniper_fixture while it unused
# pylint: disable=W0611
from services.adapters.juniper_service import JuniperService, juniper_fixture
from test_credentials.test_juniper_credentials import (SOME_DEVICE_ID,
                                                       client_details)
from test_helpers.adapter_test_base import AdapterTestBase


class TestJuniperAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return JuniperService()

    @property
    def some_client_id(self):
        return '@'.join([client_details['username'], client_details['host']])

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_user_id(self):
        raise NotImplementedError()

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip('Juniper is failing, AX-1569')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('No reachability test')
    def test_check_reachability(self):
        pass
