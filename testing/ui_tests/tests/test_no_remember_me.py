import pytest
from selenium.common.exceptions import NoSuchElementException

from ui_tests.tests.ui_test_base import TestBase


class TestNoRemeberMe(TestBase):
    def test_no_remember_me_login(self):
        self.settings_page.switch_to_page()
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        assert self.login_page.find_remember_me_toggle()
        self.login_page.login(username=self.username, password=self.password)

        self.settings_page.switch_to_page()
        self.settings_page.click_gui_settings()
        self.settings_page.change_disable_remember_me_toggle(make_yes=True)
        self.settings_page.save_and_wait_for_toaster()
        self.login_page.logout()
        with pytest.raises(NoSuchElementException) as exception_info:
            self.login_page.find_remember_me_toggle()
        assert exception_info.match('Message: no such element:.*remember_me.*')
        self.login_page.login(username=self.username, password=self.password, remember_me=False)
        self.settings_page.switch_to_page()
        self.settings_page.click_gui_settings()
        self.settings_page.change_disable_remember_me_toggle(make_yes=False)
        self.settings_page.save_and_wait_for_toaster()
