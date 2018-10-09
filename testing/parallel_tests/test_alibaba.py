# pylint: disable=unused-import
from services.adapters.alibaba_service import AlibabaService, alibaba_fixture
from test_credentials.test_alibaba_credentials import (CLIENT_DETAILS,
                                                       SOME_DEVICE_ID)
from test_helpers.adapter_test_base import AdapterTestBase


class TestAlibabaAdapter(AdapterTestBase):
    @property
    def some_user_id(self):
        raise NotImplementedError

    @property
    def adapter_service(self):
        return AlibabaService()

    @property
    def some_client_id(self):
        return CLIENT_DETAILS['access_key_id']

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    def test_check_reachability(self):
        pass

    def test_fetch_devices(self):
        pass
