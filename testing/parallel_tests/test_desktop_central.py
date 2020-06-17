import pytest
from services.adapters.desktop_central_service import desktop_central_fixture, DesktopCentralService
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_desktop_central_credentials import *


class TestDesktopCentralAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return DesktopCentralService()

    @property
    def some_client_id(self):
        return None

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip('AX-2178')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('AX-2178')
    def test_check_reachability(self):
        pass
