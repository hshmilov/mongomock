import pytest
from services.adapters.aws_service import AwsService, aws_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_aws_credentials import *


class TestAwsAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return AwsService()

    @property
    def some_client_id(self):
        return client_details[0]['aws_access_key_id']

    def get_some_client_id(self, client_count=0):
        return client_details[client_count]['aws_access_key_id']

    @property
    def some_client_details(self):
        return client_details[0]

    def get_some_client_details(self, client_count=None):
        if client_count is None:
            return client_details
        else:
            return client_details[client_count]

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID[0]

    def get_some_device_id(self, client_count=0):
        return SOME_DEVICE_ID[client_count]

    def test_proxy(self):
        self.drop_clients()
        self.adapter_service.add_client(client_ec2_with_proxy)  # set client to use proxy
        assert self.get_some_client_id(0) in self.adapter_service.devices()
        self.adapter_service.add_client(client_details[0])  # restore
        self.adapter_service.add_client(client_ecs_with_proxy)  # set client to use proxy
        assert self.get_some_client_id(1) in self.adapter_service.devices()
        self.adapter_service.add_client(client_details[1])  # restore

    def test_fetch_devices(self):
        if type(self.get_some_client_details()) is not list:
            self.adapter_service.add_client(self.some_client_details)
            self.axonius_system.assert_device_aggregated(
                self.adapter_service, [(self.some_client_id, self.some_device_id)])
        else:
            for client_count in range(len(self.get_some_client_details())):
                self.adapter_service.add_client(self.get_some_client_details(client_count))
                self.axonius_system.assert_device_aggregated(self.adapter_service, [(
                    self.get_some_client_id(client_count), self.get_some_device_id(client_count))])
