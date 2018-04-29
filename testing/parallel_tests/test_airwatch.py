import pytest

from services.adapters.airwatch_service import AirwatchService, airwatch_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_airwatch_credentials import *


class TestAirwatchAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return AirwatchService()

    @property
    def some_client_id(self):
        return client_details['Airwatch_Domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
