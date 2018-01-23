import pytest
from services.axonius_service import get_service
from services.adapters.traiana_lab_machines_service import TraianaLabMacinesService, traiana_lab_machines_service
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_traiana_lab_machines_credentials import *

DEVICE_ID_FOR_CLIENT = '420'


class TestTraianaLabMachinesAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return TraianaLabMacinesService()

    @property
    def adapter_name(self):
        return 'traiana_lab_machines_adapter'

    @property
    def some_client_id(self):
        return credentials_details['api_url']

    @property
    def some_client_details(self):
        return credentials_details

    @property
    def some_device_id(self):
        return DEVICE_ID_FOR_CLIENT
