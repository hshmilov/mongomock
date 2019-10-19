# pylint: disable=R0915
from ui_tests.tests.ui_test_base import TestBase


class TestStopDiscoveryRegular(TestBase):
    def test_stop_discovery(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery(wait=False)
        self.base_page.stop_discovery()
