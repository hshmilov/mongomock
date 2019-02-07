import pytest

# pylint: disable=unused-import
from services.adapters.checkpoint_r80_service import CheckpointR80Service, checkpoint_r80_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_checkpoint_r80_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from checkpoint_r80_adapter.client_id import get_client_id


class TestCheckpointR80Adapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return CheckpointR80Service()

    @property
    def adapter_name(self):
        return 'checkpoint_r80_adapter'

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

    @pytest.mark.skip('AX-3255')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('AX-3255')
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip('AX-3255')
    def test_removing_adapter_creds_with_users(self):
        pass

    @pytest.mark.skip('AX-3255')
    def test_check_reachability(self):
        pass
