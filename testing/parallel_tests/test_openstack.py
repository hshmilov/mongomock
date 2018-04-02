from services.adapters.openstack_service import OpenstackService, openstack_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_openstack_credentials import *
from urllib3.util.url import parse_url


class TestOpenStackAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return OpenstackService()

    @property
    def some_client_id(self):
        return '{}/{}'.format(parse_url(client_details['auth_url']).hostname, client_details['project'])

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
