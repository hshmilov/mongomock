import pytest
from flaky import flaky
from services.adapters.minerva_service import MinervaService, minerva_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_minerva_credentials import *


class TestMinervaAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return MinervaService()

    @property
    def some_client_id(self):
        return client_details['domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @flaky(max_runs=2)
    def test_fetch_devices(self):
        super().test_fetch_devices()
