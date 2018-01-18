from services.adapters.qualys_scans_service import QualysScansService, qualys_scans_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_qualys_scans_credentials import *


class TestQualysScansAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return QualysScansService()

    @property
    def adapter_name(self):
        return 'qualys_scans_adapter'

    @property
    def some_client_id(self):
        return client_details['Qualys_Scans_Domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
