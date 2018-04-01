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

    def test_fetch_devices(self):
        client_details_copy = dict(self.some_client_details)
        client_details_copy['aws_secret_access_key'] = self.adapter_service.encrypt(
            self.axonius_system.core.vol_conf.password_secret(), self.some_client_details['aws_secret_access_key'])
        self.adapter_service.add_client(client_details_copy, self.axonius_system.core.vol_conf.password_secret())
        self.axonius_system.assert_device_aggregated(self.adapter_service, [(self.some_client_id, self.some_device_id)])

    def test_proxy(self):
        self.drop_clients()
        client_details_copy = dict(client_with_proxy)
        client_details_copy['aws_secret_access_key'] = self.adapter_service.encrypt(
            self.axonius_system.core.vol_conf.password_secret(), self.some_client_details['aws_secret_access_key'])
        self.adapter_service.add_client(
            client_details_copy, self.axonius_system.core.vol_conf.password_secret())  # set client to use proxy
        assert self.some_client_id in self.adapter_service.devices()
        self.adapter_service.add_client(client_details, self.axonius_system.core.vol_conf.password_secret())  # restore
