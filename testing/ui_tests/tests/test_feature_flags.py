import pytest
from selenium.common.exceptions import NoSuchElementException

from test_credentials.test_gui_credentials import AXONIUS_USER
from ui_tests.tests.ui_test_base import TestBase


class TestFeatureFlags(TestBase):
    def test_feature_flags_axonius_user(self):
        self.devices_page.switch_to_page()
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()

        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])
        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()

        self.settings_page.set_set_trial_mode()
        self.settings_page.save_and_wait_for_toaster()

        self.settings_page.refresh()
        self.settings_page.switch_to_page()

        self.settings_page.click_feature_flags()
        assert self.settings_page.is_trial_mode()

    def test_feature_flags_regular_user(self):
        self.settings_page.switch_to_page()
        with pytest.raises(NoSuchElementException):
            self.settings_page.click_feature_flags()
