import pytest
from services.adapters.azure_service import AzureService, azure_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_azure_credentials import *


class TestAzureAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return AzureService()

    @property
    def some_client_id(self):
        from azure_adapter.service import AZURE_SUBSCRIPTION_ID
        return f'{client_details[AZURE_SUBSCRIPTION_ID]}_{client_details[AZURE_TENANT_ID]}'

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip('No reachability test')
    def test_check_reachability(self):
        pass
