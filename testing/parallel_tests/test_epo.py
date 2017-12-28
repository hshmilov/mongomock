import pytest
from services.adapters.epo_service import EpoService, epo_fixture
from test_helpers.adapter_test_base import AdapterTestBase

client_details = {
    "admin_password": "6c=xz@OACxaefu)h38MFLD%dpiTeQu$=",
    "admin_user": "administrator",
    "host": "10.0.255.180",
    "port": 8443,
    "query_user": "administrator",
    "query_password": "6c=xz@OACxaefu)h38MFLD%dpiTeQu$="
}

SOME_DEVICE_ID = '6D57ECC5-88FA-4B77-BB7C-76D1EB7AEE4B'


class TestEpoAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return EpoService()

    @property
    def adapter_name(self):
        return 'epo_adapter'

    @property
    def some_client_id(self):
        return client_details['host']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    def test_client_status_change(self):
        """
        This tests that client status changes if some change occurred in the credentials given for a client.
        It starts by adding a client with a name as its host and fetching its devices successfully.
        Then the name is mapped to the wrong IP and fetching its devices is expected to fail.
        Thus the status of the client in the DB should eventually be "error"
        :return:
        """
        self.axonius_service.db.client[self.adapter_service.unique_name].drop_collection('clients')

        def _verify_client_status(status):
            current_client = adapter_db['clients'].find_one()
            assert current_client['status'] == status

        # Copy current hosts and add host translation for client's IP to a name
        self.adapter_service.run_command_in_container("cp /etc/hosts /etc/hosts.orig")
        self.adapter_service.run_command_in_container(
            "echo {0} >> /etc/hosts".format("{0} {1}".format(self.some_client_id, self.adapter_name)))

        adapter_db = self.axonius_service.db.client[self.adapter_service.unique_name]

        # Add client to adapter, using name given defined in host translation
        self.adapter_service.add_client({**self.some_client_details, **{"host": self.adapter_name}})
        _verify_client_status("success")
        devices_as_dict = self.adapter_service.devices()
        _verify_client_status("success")
        assert len(devices_as_dict) > 0, "Got no devices although expected some"

        # Revert to original hosts and add translation for same name to an incorrect IP
        self.adapter_service.run_command_in_container("cp /etc/hosts.orig /etc/hosts")
        self.adapter_service.run_command_in_container(
            "echo {0} >> /etc/hosts".format("{0} {1}".format(self.some_client_id[:-1], self.adapter_name)))
        devices_as_dict = self.adapter_service.devices()
        _verify_client_status("error")
        assert len(devices_as_dict) == 0, "Got devices although expected none"

        # Revert to original hosts
        self.adapter_service.run_command_in_container("cp /etc/hosts.orig /etc/hosts")
        self.adapter_service.run_command_in_container("rm /etc/hosts.orig")

        adapter_db.drop_collection('clients')
