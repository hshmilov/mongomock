import pytest

from services.adapters.sccm_service import SccmService, sccm_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_sccm_credentials import *


class TestSccmAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return SccmService()

    @property
    def adapter_name(self):
        return 'sccm_adapter'

    @property
    def some_client_id(self):
        return client_details['server']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
