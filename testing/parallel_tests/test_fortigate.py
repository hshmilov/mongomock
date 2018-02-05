import pytest
from services.adapters.fortigate_service import FortigateService, fortigate_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_fortigate_credentials import *


class TestFortigateAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return FortigateService()

    @property
    def adapter_name(self):
        return 'fortigate_adapter'

    @property
    def some_client_id(self):
        return ':'.join([fortigate_details['host'], fortigate_details['port']])

    @property
    def some_client_details(self):
        return fortigate_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
