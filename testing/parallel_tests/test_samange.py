# pylint: disable=unused-import
import pytest

from services.adapters.samange_service import SamangeService, samange_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_samange_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from samange_adapter.client_id import get_client_id


class TestSamangeAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return SamangeService()

    @property
    def adapter_name(self):
        return 'samange_adapter'

    @property
    def some_client_id(self):
        return get_client_id(CLIENT_DETAILS)

    @property
    def some_client_detials(self):
        return CLIENT_DETAILS

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @property
    def some_user_id(self):
        raise NotImplementedError()

    @pytest.mark.skip('not working')
    def test_fetch_devices(self):
        pass
