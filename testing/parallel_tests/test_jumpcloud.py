# pylint: disable=unused-import
from services.adapters.jumpcloud_service import JumpcloudService, jumpcloud_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_jumpcloud_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from jumpcloud_adapter.client_id import get_client_id


class TestJumpcloudAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return JumpcloudService()

    @property
    def adapter_name(self):
        return 'jumpcloud_adapter'

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
