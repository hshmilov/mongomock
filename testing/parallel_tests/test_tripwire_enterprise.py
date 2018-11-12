# we need fixture so ignore unused
# pylint: disable=W0611
import pytest
from tripwire_enterprise_adapter.client_id import get_client_id
from services.adapters.tripwire_enterprise_service import TripwireEnterpriseService, tripwire_enterprise_fixture
from test_credentials.test_tripwire_enterprise_credentials import (CLIENT_DETAILS, SOME_DEVICE_ID)
from test_helpers.adapter_test_base import AdapterTestBase


class TestTripwireEnterpriseAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return TripwireEnterpriseService()

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
        raise NotImplementedError

    @pytest.mark.skip('No instance')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('AX-2468')
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip('AX-2468')
    def test_removing_adapter_creds_with_users(self):
        pass

    @pytest.mark.skip('AX-2468')
    def test_check_reachability(self):
        pass
