from services.adapters.cylance_service import cylance_fixture, CylanceService
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_cylance_credentials import *
import pytest


class TestCylanceAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return CylanceService()

    @property
    def adapter_name(self):
        return 'cylance_adapter'

    @property
    def some_client_id(self):
        return client_details['domain'] + '_' + client_details['tid'] + '_' + client_details['app_id']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
