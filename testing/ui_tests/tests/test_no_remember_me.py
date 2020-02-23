import time

from ui_tests.pages.page import TAB_BODY
from ui_tests.tests.ui_test_base import TestBase


class TestNoRemeberMe(TestBase):
    def test_no_remember_me_login(self):
        self.settings_page.switch_to_page()
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        time.sleep(1)
        assert self.login_page.find_remember_me_toggle()
        self.login_page.login(username=self.username, password=self.password, remember_me=True)

        self.settings_page.switch_to_page()
        self.settings_page.click_gui_settings()
        self.settings_page.click_toggle_button(
            self.settings_page.find_session_timeout_toggle(), make_yes=True, window=TAB_BODY)
        self.settings_page.click_toggle_button(self.settings_page.find_disable_remember_me_toggle(),
                                               make_yes=True, scroll_to_toggle=True)
        self.settings_page.save_and_wait_for_toaster()
        self.login_page.logout()
        try:
            self.login_page.find_remember_me_toggle()
            assert False
        except Exception:
            # As expected
            pass
        time.sleep(1)
        self.login_page.login(username=self.username, password=self.password, remember_me=False)
        self.settings_page.switch_to_page()
        self.settings_page.click_gui_settings()
        self.settings_page.click_toggle_button(self.settings_page.find_disable_remember_me_toggle(),
                                               make_yes=False, scroll_to_toggle=True)
        self.settings_page.save_and_wait_for_toaster()
