# pylint: disable=unused-import
from services.adapters.wazuh_service import WazuhService, wazuh_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_wazuh_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from wazuh_adapter.client_id import get_client_id


class TestWazuhAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return WazuhService()

    @property
    def adapter_name(self):
        return 'wazuh_adapter'

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
