from services.adapters.qualys_service import QualysService, qualys_fixture
from test_helpers.adapter_test_base import AdapterTestBase


client_details = {
    "Qualys_Domain": "qualysapi.qg2.apps.qualys.eu",
    "username": "axnus5fs",
    "password": "7ldUJKtYG8oe1243fds"
}

SOME_DEVICE_ID = '1d05fe7f-7abe-4087-9e32-9c39a2442e94'  # ip-10-0-229-166 test-qualys-linux


class TestQualysAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return QualysService()

    @property
    def adapter_name(self):
        return 'qualys_adapter'

    @property
    def some_client_id(self):
        return client_details['Qualys_Domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
