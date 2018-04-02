from services.adapters.qualys_service import QualysService, qualys_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_qualys_credentials import *


class TestQualysAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return QualysService()

    @property
    def some_client_id(self):
        return client_details['Qualys_Domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
