# pylint: disable=unused-import
from services.adapters.claroty_service import clartoy_fixture, ClarotyService
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_claroty_credentials import CLIENTS_DETAILS, SOME_DEVICE_ID
import pytest


class TestClarotyAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return ClarotyService()

    @property
    def adapter_name(self):
        return 'claroty_adapter'

    @property
    def some_client_id(self):
        return CLIENTS_DETAILS['domain']

    @property
    def some_client_details(self):
        return CLIENTS_DETAILS

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("Problem with claroty.")
    def test_fetch_devices(self):
        pass
