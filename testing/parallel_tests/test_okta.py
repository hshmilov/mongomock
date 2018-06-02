import pytest

from services.adapters.okta_service import OktaService, okta_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_okta_credentials import *


class TestOktaAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return OktaService()

    @property
    def some_client_id(self):
        # TODO: replace those lines. Because requirements.txt take a while to fix
        # return OktaAdapter._get_client_id(None, client_details)
        import hashlib
        api_declassified = hashlib.md5(client_details['api_key'].encode('utf-8')).hexdigest()
        return f"{client_details['url']}_{api_declassified}"

    @property
    def some_client_details(self):
        return client_details

    def test_fetch_devices(self):
        return  # we can't test that - we don't return devices

    def test_fetch_users(self):
        self.adapter_service.add_client(self.some_client_details)
        # send trigger to agg to refresh devices
        self.axonius_system.aggregator.query_devices(adapter_id=self.adapter_service.unique_name)
        users_list = self.axonius_system.get_users_with_condition(
            {
                "adapters.data.id": self.some_user_id,
            }
        )
        assert len(users_list) == 1, f"Did not find user {self.some_user_id}"

    @property
    def some_user_id(self):
        return SOME_USER_ID
