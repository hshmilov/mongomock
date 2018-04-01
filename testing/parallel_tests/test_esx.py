import pytest
from services.adapters.esx_service import EsxService, esx_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_esx_credentials import *


class TestEsxAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return EsxService()

    @property
    def adapter_name(self):
        return 'esx_adapter'

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    def test_fetch_devices(self):
        client_details_to_send = []
        for client, some_device_id in client_details:
            self.adapter_service.add_client(client)

            client_id = "{}/{}".format(client['host'], client['user'])
            client_details_to_send.append((client_id, some_device_id))
        self.axonius_system.assert_device_aggregated(self.adapter_service, client_details_to_send)

    def test_folder_on_dc_level(self):
        self.drop_clients()

        client, _ = client_details[0]

        client_id = "{}/{}".format(client['host'], client['user'])
        self.adapter_service.add_client(client)

        self.axonius_system.assert_device_aggregated(self.adapter_service, [(client_id, AGGREGATED_DEVICE_ID)])
