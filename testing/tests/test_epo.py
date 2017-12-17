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
        return EpoService(should_start=False)

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
