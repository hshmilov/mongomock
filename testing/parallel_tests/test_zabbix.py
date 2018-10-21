# we need fixture so ignore unused
# pylint: disable=W0611
import pytest
from services.adapters.zabbix_service import ZabbixService, zabbix_fixture
from test_credentials.test_zabbix_credentials import (CLIETN_DETAILS,
                                                      SOME_DEVICE_ID)
from test_helpers.adapter_test_base import AdapterTestBase


class TestZabbixAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return ZabbixService()

    @property
    def some_client_id(self):
        return CLIETN_DETAILS['domain'] + '_' + CLIETN_DETAILS['username']

    @property
    def some_client_details(self):
        return CLIETN_DETAILS

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @property
    def some_user_id(self):
        raise NotImplementedError

    @pytest.mark.skip('No instance')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('No instance')
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip('No instance')
    def test_removing_adapter_creds_with_users(self):
        pass

    @pytest.mark.skip('No instance')
    def test_check_reachability(self):
        pass
