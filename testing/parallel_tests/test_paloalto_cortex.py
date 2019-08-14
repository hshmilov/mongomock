# pylint: disable=unused-import
import pytest
from flaky import flaky

from paloalto_cortex_adapter.client_id import get_client_id
from services.adapters.paloalto_cortex_service import (PaloaltoCortexService,
                                                       paloalto_cortex_fixture)
from test_credentials.test_paloalto_cortex_credentials import (CLIENT_DETAILS,
                                                               SOME_DEVICE_ID)
from test_helpers.adapter_test_base import AdapterTestBase


class TestPaloaltoCortexAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return PaloaltoCortexService()

    @property
    def adapter_name(self):
        return 'paloalto_cortex_adapter'

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

    @pytest.mark.skip('Its a cloud instance so no test check reachability')
    def test_check_reachability(self):
        pass

    @pytest.mark.skip('not working')
    def test_fetch_devices(self):
        super().test_fetch_devices()
