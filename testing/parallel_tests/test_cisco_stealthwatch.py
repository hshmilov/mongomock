import pytest

# pylint: disable=unused-import
from services.adapters.cisco_stealthwatch_service import CiscoStealthwatchService, cisco_stealthwatch_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_cisco_stealthwatch_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from cisco_stealthwatch_adapter.client_id import get_client_id


class TestCiscoStealthwatchAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return CiscoStealthwatchService()

    @property
    def adapter_name(self):
        return 'cisco_stealthwatch_adapter'

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
    def test_check_reachability(self):
        pass

    @pytest.mark.skip('no server')
    def test_fetch_devices(self):
        pass
