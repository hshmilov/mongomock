import pytest
from services.adapters.aws_service import AwsService, aws_fixture
from test_helpers.adapter_test_base import AdapterTestBase

client_details = {
    "aws_access_key_id": "AKIAJOCJ5PGEAR6LNIFQ",
    "aws_secret_access_key": "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",
    "region_name": "us-east-2"
}

SOME_DEVICE_ID = 'i-0ec91cae8a42be974'


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
