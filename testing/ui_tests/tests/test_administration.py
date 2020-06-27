from selenium.common.exceptions import NoSuchElementException

from axonius.utils.wait import wait_until
from ui_tests.tests.ui_test_base import TestBase


class TestAdministration(TestBase):
    def test_configuration_script_upload(self):
        self.dashboard_page.wait_for_trial_banner()
        self.dashboard_page.switch_to_page()
        assert self.dashboard_page.find_trial_remainder_banner(30)
        self.administration_page.switch_to_page()
        self.administration_page.upload_configuration_script('remove_trial_v2.py.tar')
        self.administration_page.execute_configuration_script()
        self.dashboard_page.switch_to_page()
        wait_until(self._check_no_trial_banner, interval=10)

    def _check_no_trial_banner(self):
        self.dashboard_page.refresh()
        try:
            self.dashboard_page.try_to_find_trial_banner()
        except NoSuchElementException:
            return True
        return False
