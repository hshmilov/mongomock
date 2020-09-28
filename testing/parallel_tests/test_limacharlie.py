# pylint: disable=unused-import
from services.adapters.limacharlie_service import LimacharlieService, limacharlie_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_limacharlie_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from limacharlie_adapter.client_id import get_client_id


class TestLimacharlieAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return LimacharlieService()

    @property
    def adapter_name(self):
        return 'limacharlie_adapter'

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

    @property
    def adapter_has_constant_url(self):
        return True
