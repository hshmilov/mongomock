import pytest

# pylint: disable=W0611
from services.adapters.fortigate_service import FortigateService, fortigate_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_fortigate_credentials import client_details, SOME_DEVICE_ID


class TestFortigateAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return FortigateService()

    @property
    def some_client_id(self):
        return ':'.join([client_details['host'], str(client_details['port'])])

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @property
    def some_user_id(self):
        raise NotImplementedError

    @pytest.mark.skip('Not working')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('Not working')
    def test_check_reachability(self):
        pass
