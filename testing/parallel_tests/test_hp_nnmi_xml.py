import pytest

# pylint: disable=unused-import
from services.adapters.hp_nnmi_xml_service import HpNnmiXmlService, hp_nnmi_xml_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_hp_nnmi_xml_credentials import CLIENT_DETAILS, SOME_DEVICE_ID


class TestHpNnmiXmlAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return HpNnmiXmlService()

    @property
    def adapter_name(self):
        return 'hp_nnmi_xml_adapter'

    @property
    def some_client_id(self):
        return f'HP_NNMI_XML_{CLIENT_DETAILS.get("user_id", "UNKNOWN")}'

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @property
    def some_user_id(self):
        raise NotImplementedError()

    @pytest.mark.skip('no server')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('no server')
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip('no server')
    def test_removing_adapter_creds_with_users(self):
        pass

    @pytest.mark.skip('no server')
    def test_check_reachability(self):
        pass
