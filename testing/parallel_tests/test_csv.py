import pytest
from services.adapters.csv_service import CsvService, csv_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_csv_credentials import *


class TestCsvAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return CsvService()

    @property
    def adapter_name(self):
        return 'csv_adapter'

    @property
    def some_client_id(self):
        return client_details['user_id']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
