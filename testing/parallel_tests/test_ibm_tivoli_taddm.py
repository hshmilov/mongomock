import pytest
# pylint: disable=unused-import
# pylint: disable=abstract-method
from services.adapters.ibm_tivoli_taddm_service import IbmTivoliTaddmService, ibm_tivoli_taddm_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_ibm_tivoli_taddm_credentials import client_details, SOME_DEVICE_ID
from ibm_tivoli_taddm_adapter.client_id import get_client_id


class TestIbmTivoliTaddmAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return IbmTivoliTaddmService()

    @property
    def some_client_id(self):
        return get_client_id(client_details)

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip('AX-2644')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('AX-2644')
    def test_check_reachability(self):
        pass
