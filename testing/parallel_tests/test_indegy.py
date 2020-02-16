import pytest
# pylint: disable=unused-import
from services.adapters.indegy_service import IndegyService, indegy_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_indegy_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from indegy_adapter.client_id import get_client_id


class TestIndegyAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return IndegyService()

    @property
    def adapter_name(self):
        return 'indegy_adapter'

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

    @pytest.mark.skip('Hangs sometimes')
    def test_fetch_devices(self):
        super().test_fetch_devices()
