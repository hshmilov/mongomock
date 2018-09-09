import pytest

from esx_adapter.service import EsxAdapter
from services.adapters.esx_service import EsxService, esx_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_bad_credentials import FAKE_CLIENT_DETAILS
from test_credentials.test_esx_credentials import *


class TestEsxAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return EsxService()

    @property
    def some_client_id(self):
        return EsxAdapter._get_client_id(None, self.some_client_details)

    @property
    def some_client_details(self):
        return dict(client_details[0][0])

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    def test_fetch_devices(self):
        client_details_to_send = []
        for client, some_device_id in client_details:
            client = dict(client)
            self.adapter_service.add_client(client)

            client_id = "{}/{}".format(client['host'], client['user'])
            client_details_to_send.append((client_id, some_device_id))
        self.axonius_system.assert_device_aggregated(self.adapter_service, client_details_to_send)
        assert not self.axonius_system.get_device_by_id(self.adapter_service.unique_name, VERIFY_DEVICE_MISSING)

    def test_folder_on_dc_level(self):
        self.drop_clients()

        client, _ = client_details[0]
        client = dict(client)

        client_id = "{}/{}".format(client['host'], client['user'])
        self.adapter_service.add_client(client)

        self.axonius_system.assert_device_aggregated(self.adapter_service, [(client_id, AGGREGATED_DEVICE_ID)])

    def test_check_reachability(self):
        assert self.adapter_service.is_client_reachable(self.some_client_details)
        assert not self.adapter_service.is_client_reachable(FAKE_CLIENT_DETAILS)
