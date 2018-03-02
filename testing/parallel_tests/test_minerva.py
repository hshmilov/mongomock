import pytest

from services.adapters.minerva_service import MinervaService, minerva_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_minerva_credentials import *


class TestMinervaAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return MinervaService()

    @property
    def adapter_name(self):
        return 'minerva_adapter'

    @property
    def some_client_id(self):
        return client_details['Minerva_Domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
