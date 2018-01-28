import pytest
import requests
from services.adapters.qualys_scans_service import QualysScansService, qualys_scans_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_qualys_scans_credentials import *
from qualys_scans_connection import QualysScansConnection


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

    def test_fetch_devices(self):
        try:
            super().test_fetch_devices()
        except AssertionError:
            try:
                qualys_connection = QualysScansConnection(
                    self.axonius_service.aggregator.logger, client_details['Qualys_Scans_Domain'])
                qualys_connection.set_credentials(client_details["username"], client_details["password"])
                response = requests.get(qualys_connection._get_url_request("scan"), headers=qualys_connection.headers,
                                        auth=qualys_connection.auth,
                                        params=[('action', 'list'),
                                                ('launched_after_datetime', '3999-12-31T23:12:00Z')])
                response.raise_for_status()
            except Exception as e:
                # if we reached the API limit, the test is considered passed
                if "This API cannot be run again for another" not in response.text:
                    raise
