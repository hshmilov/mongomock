# pylint: disable=unused-import
from services.adapters.orca_service import OrcaService, orca_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_orca_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from orca_adapter.client_id import get_client_id


class TestOrcaAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return OrcaService()

    @property
    def adapter_name(self):
        return 'orca_adapter'

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
