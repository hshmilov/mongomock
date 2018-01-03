from services.adapters.esx_service import EsxService, esx_fixture
from test_helpers.adapter_test_base import AdapterTestBase


client_details = [
    ({
        "host": "vcenter.axonius.lan",
        "user": "administrator@vsphere.local",
        "password": "Br!ng0rder",
        "verify_ssl": False
    }, '52e71bcb-db64-fe5e-40bf-8f5aa36f1e6b'),
    # This vcenter is currently not active!!! we should return it as soon as it becomes active again
    # ({
    #     "host": "vcenter51.axonius.lan",
    #     "user": "root",
    #     "password": "vmware",
    #     "verify_ssl": False
    # }, "525345eb-51ef-f4d7-85bb-08e521b94528"),
    ({
        "host": "vcenter55.axonius.lan",
        "user": "root",
        "password": "vmware",
        "verify_ssl": False
    }, "525d738d-c18f-ed57-6059-6d3378a61442")]

# vcenter vm
SOME_DEVICE_ID = '52e71bcb-db64-fe5e-40bf-8f5aa36f1e6b'


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

        for client, some_device_id in client_details:
            client_id = "{}/{}".format(client['host'], client['user'])
            axonius_service.add_client_to_adapter(self.adapter_service, client)
            axonius_service.assert_device_aggregated(self.adapter_service, client_id, some_device_id)

    def test_folder_on_dc_level(self):
        axonius_service = self.axonius_service
        axonius_service.clear_all_devices()
        client, _ = client_details[0]

        client_id = "{}/{}".format(client['host'], client['user'])
        axonius_service.add_client_to_adapter(self.adapter_service, client)

        # this is the ID of a VM that is inside a datacenter that is inside a folder
        # it is called "just_for_datacenter_folders"
        axonius_service.assert_device_aggregated(
            self.adapter_service, client_id, "5011b327-7833-4d80-af9f-11c0afdde448")
