import pytest
from services.adapters.aws_service import AwsService, aws_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_aws_credentials import *


class TestAwsAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return AwsService()

    @property
    def adapter_name(self):
        return 'aws_adapter'

    @property
    def some_client_id(self):
        return client_details['aws_access_key_id']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    def test_proxy(self):
        self.drop_clients()
        self.adapter_service.add_client(client_with_proxy)  # set client to use proxy
        assert self.some_client_id in self.adapter_service.devices()
        self.adapter_service.add_client(client_details)  # restore
