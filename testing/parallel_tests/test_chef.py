import pytest

from services.adapters.chef_service import ChefService, chef_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_chef_credentials import *


class TestChefAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return ChefService()

    @property
    def some_client_id(self):
        return client_details['domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
