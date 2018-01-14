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
        axonius_service = self.axonius_service

        for client, _ in client_details:
            self.adapter_service.add_client(client)

        for client, some_device_id in client_details:
            client_id = "{}/{}".format(client['host'], client['user'])
            axonius_service.assert_device_aggregated(self.adapter_service, client_id, some_device_id)

    def test_folder_on_dc_level(self):
        axonius_service = self.axonius_service
        self.drop_clients()

        client, _ = client_details[0]

        client_id = "{}/{}".format(client['host'], client['user'])
        self.adapter_service.add_client(client)

        axonius_service.assert_device_aggregated(
            self.adapter_service, client_id, AGGREGATED_DEVICE_ID)
