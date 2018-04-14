import pytest
from services.adapters.observeit_csv_service import observeit_csv_fixture, ObserveitCsvService
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_observeit_csv_credentials import *


class TestObserveitCsvAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return ObserveitCsvService()

    @property
    def some_client_id(self):
        return client_details['user_id']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
