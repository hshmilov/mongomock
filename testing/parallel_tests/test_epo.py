import pytest
from services.adapters.epo_service import EpoService, epo_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_epo_credentials import *


class TestEpoAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return EpoService()

    @property
    def some_client_id(self):
        return client_details['host']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("EPO License expired")
    def test_fetch_devices(self):
        """
        We put it here to disable the super().test_fetch_devices func which will fail.
        Once we have a license, remove this func.
        :return:
        """
        pass

    @pytest.mark.skip("EPO License Expired")
    def test_client_status_change(self):
        """
        This tests that client status changes if some change occurred in the credentials given for a client.
        It starts by adding a client with a name as its host and fetching its devices successfully.
        Then the name is mapped to the wrong IP and fetching its devices is expected to fail.
        Thus the status of the client in the DB should eventually be "error"
        :return:
        """
        self.drop_clients()

        def _verify_client_status(status):
            current_client = adapter_db['clients'].find_one()
            assert current_client['status'] == status

        adapter_db = self.axonius_system.db.client[self.adapter_service.unique_name]

        # Add client to adapter, using name given defined in host translation
        self.adapter_service.add_client(self.some_client_details)
        _verify_client_status("success")
        devices_as_dict = self.adapter_service.devices()
        _verify_client_status("success")
        assert len(devices_as_dict) > 0, "Got no devices although expected some"

        self.adapter_service.add_client({**self.some_client_details, 'port': 1})
        _verify_client_status("error")

        devices_as_dict = self.adapter_service.devices()
        assert len(devices_as_dict) == 0, "Got devices although expected none"

        adapter_db.drop_collection('clients')
