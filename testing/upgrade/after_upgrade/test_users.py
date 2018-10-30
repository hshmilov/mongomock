import pytest
from selenium.common.exceptions import NoSuchElementException, WebDriverException

from ui_tests.pages.adapters_page import AdaptersPage
from ui_tests.tests import ui_consts
from ui_tests.tests.ui_test_base import TestBase


class TestPrepareUsers(TestBase):
    def test_hidden_user(self):
        self.login_page.logout()
        self.login_page.login(ui_consts.HIDDEN_USER_NAME, ui_consts.HIDDEN_USER_NEW_PASSWORD)
        self.login_page.logout()

    def test_restricted_user(self):
        self.settings_page.switch_to_page()
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.wait_for_spinner_to_end()
        self.login_page.login(username=ui_consts.RESTRICTED_USERNAME, password=ui_consts.NEW_PASSWORD)

        # check restricted screens
        for screen in self.get_all_screens():
            if isinstance(screen, AdaptersPage):
                continue
            screen.assert_screen_is_restricted()

        # check readonly screen
        with pytest.raises(NoSuchElementException):
            self.adapters_page.assert_screen_is_restricted()

        # assert it's readonly
        self.adapters_page.switch_to_page()
        self.adapters_page.click_adapter('Active Directory')
        self.adapters_page.wait_for_table_to_load()
        with pytest.raises(WebDriverException):
            self.adapters_page.click_new_server()
