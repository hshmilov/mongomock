# pylint: disable=unused-import
from services.adapters.endgame_service import EndgameService, endgame_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_endgame_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from endgame_adapter.client_id import get_client_id


class TestEndgameAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return EndgameService()

    @property
    def adapter_name(self):
        return 'endgame_adapter'

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
