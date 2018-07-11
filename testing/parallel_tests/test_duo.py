from services.adapters.duo_service import DuoService, duo_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_duo_credentials import *
from duo_adapter.service import DuoAdapter
import pytest


class TestDuoAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return DuoService()

    @property
    def some_client_id(self):
        return DuoAdapter._get_client_id(None, client_details)

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_user_id(self):
        return SOME_USER_ID

    def test_fetch_devices(self):
        # no devices in this adapter
        return
