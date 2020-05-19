import pytest

# pylint: disable=unused-import
from services.adapters.g_naapi_service import GNaapiService, g_naapi_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_g_naapi_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from g_naapi_adapter.client_id import get_client_id


class TestGNaapiAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return GNaapiService()

    @property
    def adapter_name(self):
        return 'g_naapi_adapter'

    @property
    def some_client_id(self):
        return get_client_id(CLIENT_DETAILS)

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @property
    def some_user_id(self):
        raise NotImplementedError()

    @pytest.mark.skip('Skip untili make this work just once')
    def test_fetch_devices(self):
        ##################################################################################
        ## DO NOT PYTEST.MARK.SKIP THIS FUNCTION. IT USES A MOCK SERVER AND IF IT IS    ##
        ## NOT WORKING THAN IT REALLY BROKE. THIS CAN HAPPEN IF YOU CHANGED SOMETHING   ##
        ## IN AWS, BECAUSE IT HEAVILY DEPENDS ON AWS                                    ##
        ##################################################################################
        print(f'Calling super().test_fetch_devices')
        super().test_fetch_devices()

    @pytest.mark.skip('No test environment')
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip('No test environment')
    def test_removing_adapter_creds_with_users(self):
        pass

    @pytest.mark.skip('No test environment')
    def test_check_reachability(self):
        pass
