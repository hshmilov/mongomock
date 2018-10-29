import pytest
from selenium.common.exceptions import (InvalidElementStateException,
                                        NoSuchElementException,
                                        WebDriverException)
from ui_tests.tests import ui_consts
from ui_tests.tests.ui_test_base import TestBase


class TestUserPermissions(TestBase):
    def test_new_user_is_restricted(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(ui_consts.RESTRICTED_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME)

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=ui_consts.RESTRICTED_USERNAME, password=ui_consts.NEW_PASSWORD)
        for screen in self.get_all_screens():
            screen.assert_screen_is_restricted()

    def test_new_read_only_user(self):
        self.settings_page.switch_to_page()

        # to fill up devices and users
        self.base_page.run_discovery()

        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(ui_consts.RESTRICTED_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME)

        self.settings_page.wait_for_toaster('User created.')

        for label in self.settings_page.get_permission_labels():
            self.settings_page.select_permissions(label, self.settings_page.READ_ONLY_PERMISSION)

        self.settings_page.click_save_manage_users_settings()

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=ui_consts.RESTRICTED_USERNAME, password=ui_consts.NEW_PASSWORD)

        for screen in self.get_all_screens():
            with pytest.raises(NoSuchElementException):
                screen.assert_screen_is_restricted()

        self.adapters_page.switch_to_page()
        self.adapters_page.click_adapter('Active Directory')
        self.adapters_page.wait_for_table_to_load()
        with pytest.raises(WebDriverException):
            self.adapters_page.click_new_server()

        self.alert_page.switch_to_page()
        with pytest.raises(NoSuchElementException):
            self.alert_page.find_new_alert_button()

        self.report_page.switch_to_page()
        with pytest.raises(InvalidElementStateException):
            self.report_page.fill_email(ui_consts.VALID_EMAIL)

        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.users_page.click_row()
        with pytest.raises(NoSuchElementException):
            self.devices_page.add_new_tag(ui_consts.TAG_NAME)

        self.users_page.switch_to_page()
        self.users_page.wait_for_table_to_load()
        self.users_page.click_row()
        with pytest.raises(NoSuchElementException):
            self.devices_page.add_new_tag(ui_consts.TAG_NAME)
