import pytest

from services.adapters.bomgar_service import BomgarService, bomgar_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_bomgar_credentials import *


class TestBomgarAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return BomgarService()

    @property
    def adapter_name(self):
        return 'bomgar_adapter'

    @property
    def some_client_id(self):
        return client_details['domain'] + ':' + client_details['client_id']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("Bomgar License expired")
    def test_fetch_devices(self):
        # Our license expires on Friday, March 2nd, 2018 @ 06:00 UTC
        # so tests will stop working then...
        pass
