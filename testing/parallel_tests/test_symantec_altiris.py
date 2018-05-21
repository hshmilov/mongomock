import pytest

from services.adapters.symantec_altiris_service import SymantecAltirisService, symantec_altiris_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_symantec_altiris_credentials import *


class TestSymantecAltirisAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return SymantecAltirisService()

    @property
    def some_client_id(self):
        return client_details['server']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
