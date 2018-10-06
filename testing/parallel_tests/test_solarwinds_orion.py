import pytest

from services.adapters.solarwinds_orion_service import (SolarwindsOrionService,
                                                        solarwinds_orion_fixture)
from solarwinds_orion_adapter.service import SolarwindsOrionAdapter
from test_credentials.test_solarwinds_orion_credentials import *
from test_helpers.adapter_test_base import AdapterTestBase


class TestSolarwindsOrionAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return SolarwindsOrionService()

    @property
    def some_client_id(self):
        return SolarwindsOrionAdapter._get_client_id(None, client_details)

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
