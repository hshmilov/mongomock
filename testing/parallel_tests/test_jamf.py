import datetime
import pytest
from flaky import flaky
from axonius.plugin_base import EntityType
from services.adapters.jamf_service import JamfService, jamf_fixture
from services.axonius_service import get_service
from test_helpers.adapter_test_base import AdapterTestBase
from test_helpers.user_helper import get_user_dict
from test_credentials.test_jamf_credentials import *
from tests.conftest import axonius_fixture

GUI_TEST_PLUGIN = 'GUI_TEST_PLUGIN'


class TestJamfAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return JamfService()

    @property
    def some_client_id(self):
        return client_details['Jamf_Domain']

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    def get_user_department(self):
        axonius_system = get_service()
        devices_db = self.axonius_system.db.get_entity_db(EntityType.Devices)
        axonius_system.insert_user(get_user_dict('axonius_printer', '1112', GUI_TEST_PLUGIN,
                                                 'GUI_TEST_PLUGIN_222', user_department="Office"))
        self.test_fetch_devices()
        assert len(list(devices_db.find({"adapters.data.users.user_department": {"$exists": True}}))) == 0
        self.adapter_service.set_configurable_config("JamfAdapter", "fetch_department", True)
        self.test_fetch_devices()
        assert len(list(devices_db.find({"adapters.data.users.user_department": {"$exists": True}}))) == 1

    def test_fetch_devices(self):
        super().test_fetch_devices()
