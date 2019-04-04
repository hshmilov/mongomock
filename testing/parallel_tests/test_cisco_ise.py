# pylint: disable=unused-import
import pytest

from services.adapters.cisco_ise_service import CiscoIseService, cisco_ise_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from cisco_ise_adapter.client_id import get_client_id


class TestCiscoIseAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return CiscoIseService()

    @property
    def adapter_name(self):
        return 'cisco_ise_adapter'

    @property
    def some_client_id(self):
        return get_client_id({})

    @property
    def some_client_detials(self):
        return ''

    @property
    def some_client_details(self):
        return ''

    @property
    def some_device_id(self):
        return ''

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
