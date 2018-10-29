import pytest
from services.adapters.aws_service import AwsService, aws_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_aws_credentials import *

pytestmark = pytest.mark.sanity


def _get_id_from_client(client):
    return client['aws_access_key_id'] + client['region_name']


class TestAwsAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return AwsService()

    @property
    def some_client_id(self):
        return _get_id_from_client(client_details[0][0])

    @property
    def some_client_details(self):
        return client_details[0][0]

    @property
    def some_device_id(self):
        return client_details[0][1][0]

    @pytest.mark.skip('No reachability test')
    def test_check_reachability(self):
        pass

    @pytest.mark.skip('AX-2359')
    def test_proxy(self):
        self.drop_clients()
        self.adapter_service.add_client(client_ec2_with_proxy)  # set client to use proxy
        assert _get_id_from_client(client_details[0][0]) in self.adapter_service.devices()
        self.adapter_service.add_client(client_details[0][0])  # restore
        self.adapter_service.add_client(client_ecs_with_proxy)  # set client to use proxy
        assert _get_id_from_client(client_details[1][0]) in self.adapter_service.devices()
        self.adapter_service.add_client(client_details[1][0])  # restore

    def test_fetch_devices(self):
        for some_client, some_adapters_ids in client_details:
            some_client_id = _get_id_from_client(some_client)
            self.adapter_service.add_client(some_client)
            for some_adapters_id in some_adapters_ids:
                self.axonius_system.assert_device_aggregated(
                    self.adapter_service,
                    [(some_client_id, some_adapters_id)]
                )
