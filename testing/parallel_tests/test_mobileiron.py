import pytest

from services.adapters.mobileiron_service import MobileironService, mobileiron_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_mobileiron_credentials import *


class TestMobileironAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return MobileironService()

    @property
    def some_client_id(self):
        return client_details['Mobileiron_Domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
