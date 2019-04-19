import pytest
# we need fixture so ignore unused
# pylint: disable=W0611
from services.adapters.azure_ad_service import AzureAdService, azure_ad_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_azure_ad_credentials import client_details, SOME_DEVICE_ID, SOME_USER_ID
from azure_ad_adapter.service import AzureAdAdapter


class TestAzureAdAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return AzureAdService()

    @property
    def some_client_id(self):
        # pylint: disable=W0212
        return AzureAdAdapter._get_client_id(client_details)

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @property
    def some_user_id(self):
        return SOME_USER_ID

    @pytest.mark.skip('Not working')
    def test_check_reachability(self):
        # We only check that the client is reachable, but we don't check that a fake client is unreachable.
        # The reason is that its a cloud solution so there is no other "fake client". any other fake client
        # is actually just wrong credentials and that is certainly reachable.
        assert self.adapter_service.is_client_reachable(self.some_client_details)

    @pytest.mark.skip('Not working')
    def test_fetch_devices(self):
        pass
