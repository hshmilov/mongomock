import time

import pytest
from flaky import flaky
from selenium.common.exceptions import ElementNotInteractableException, NoSuchElementException

from axonius.utils.wait import wait_until
from services.axon_service import TimeoutException
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests import ui_consts

PASSWORD_POLICY_ERROR_MSG = 'Password does not meet the password policy requirements'


class TestChangePasswordSettings(TestBase):
    def test_change_password(self):
        self.my_account_page.switch_to_page()
        self.my_account_page.click_change_admin_password()

        # Fill in the current password
        assert self.my_account_page.is_save_button_disabled()
        self.my_account_page.fill_current_password(self.password)
        assert self.my_account_page.is_save_button_disabled()
        self.my_account_page.fill_new_password(self.password)
        assert self.my_account_page.is_save_button_disabled()
        self.my_account_page.fill_confirm_password(self.password)
        assert not self.my_account_page.is_save_button_disabled()
        self.my_account_page.click_save_button()
        self.my_account_page.wait_for_password_changed_toaster()

        # Fill in incorrect password
        self.my_account_page.change_password(ui_consts.INCORRECT_PASSWORD,
                                             ui_consts.INCORRECT_PASSWORD,
                                             ui_consts.INCORRECT_PASSWORD,
                                             self.my_account_page.wait_for_given_password_is_wrong_toaster)

        # Fill in unmacthed passwords
        self.my_account_page.change_password(self.password,
                                             ui_consts.UNMATCHED_PASSWORD1,
                                             ui_consts.UNMATCHED_PASSWORD2,
                                             self.my_account_page.wait_for_passwords_dont_match_toaster)

        # Fill in new password
        self.my_account_page.change_password(self.password,
                                             ui_consts.NEW_PASSWORD,
                                             ui_consts.NEW_PASSWORD,
                                             self.my_account_page.wait_for_password_changed_toaster)

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=self.username, password=ui_consts.INCORRECT_PASSWORD)
        assert self.login_page.wait_for_invalid_login_message()
        self.login_page.login(username=self.username, password=ui_consts.UNMATCHED_PASSWORD1)
        assert self.login_page.wait_for_invalid_login_message()
        self.login_page.login(username=self.username, password=ui_consts.UNMATCHED_PASSWORD2)
        assert self.login_page.wait_for_invalid_login_message()
        self.my_account_page.refresh()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=self.username, password=ui_consts.NEW_PASSWORD)

        self.my_account_page.switch_to_page()

        # Change password back
        self.my_account_page.change_password(ui_consts.NEW_PASSWORD,
                                             self.password,
                                             self.password,
                                             self.my_account_page.wait_for_password_changed_toaster)

    def test_password_policy(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.click_toggle_button(self.settings_page.find_password_policy_toggle(), make_yes=True)
        self.settings_page.fill_password_policy(password_length=5, min_lowercase=2, min_uppercase=3,
                                                min_special_chars=1, min_numbers=2)
        # Make sure the validation work as it should
        with pytest.raises(ElementNotInteractableException):
            self.settings_page.click_save_global_settings()

        self.settings_page.fill_password_policy(password_length=10, min_lowercase=2, min_uppercase=3,
                                                min_special_chars=1, min_numbers=2)
        self.settings_page.click_save_global_settings()

        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(ui_consts.RESTRICTED_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME,
                                           self.settings_page.RESTRICTED_ROLE,
                                           wait_for_toaster=False)

        self.settings_page.assert_server_error(PASSWORD_POLICY_ERROR_MSG)

        self.settings_page.safe_refresh()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(ui_consts.RESTRICTED_USERNAME,
                                           'aaaBBB!123123',
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME,
                                           self.settings_page.RESTRICTED_ROLE)

        self.settings_page.click_edit_user(ui_consts.RESTRICTED_USERNAME)
        self.settings_page.fill_password_field('kjfsk8978')
        self.settings_page.click_save_button()
        self.settings_page.assert_server_error(PASSWORD_POLICY_ERROR_MSG)

        self.settings_page.safe_refresh()
        self.settings_page.click_manage_users_settings()

        self.my_account_page.switch_to_page()
        self.my_account_page.click_change_admin_password()
        self.my_account_page.fill_current_password(self.password)
        self.my_account_page.fill_new_password('aaabbb43')
        self.my_account_page.fill_confirm_password('aaabbb43')
        self.my_account_page.click_save_button()
        assert wait_until(self.my_account_page.get_user_dialog_error,
                          tolerated_exceptions_list=[NoSuchElementException]) == PASSWORD_POLICY_ERROR_MSG

        # Cleanup
        self.account_page.safe_refresh()
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.click_toggle_button(self.settings_page.find_password_policy_toggle(), make_yes=False)
        self.settings_page.click_save_global_settings()
        self.settings_page.click_manage_users_settings()
        try:
            self.settings_page.remove_user_by_user_name_with_selection(ui_consts.RESTRICTED_USERNAME)
        except TimeoutException:
            assert ui_consts.RESTRICTED_USERNAME not in list(self.settings_page.get_all_user_names())

    @flaky(max_runs=2)
    def test_gui_restart_keeps_password(self):
        self.my_account_page.switch_to_page()
        self.my_account_page.click_change_admin_password()

        # Fill in new password
        self.my_account_page.change_password(self.password,
                                             ui_consts.NEW_PASSWORD,
                                             ui_consts.NEW_PASSWORD,
                                             self.my_account_page.wait_for_password_changed_toaster)

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()

        gui_service = self.axonius_system.gui
        gui_service.take_process_ownership()
        gui_service.stop(should_delete=False)
        gui_service.start_and_wait()
        time.sleep(5)

        # Check that we can log in with the new password
        self.my_account_page.refresh()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=self.username, password=ui_consts.NEW_PASSWORD)
        self.my_account_page.switch_to_page()

        # Change password back
        self.my_account_page.change_password(ui_consts.NEW_PASSWORD,
                                             self.password,
                                             self.password,
                                             self.my_account_page.wait_for_password_changed_toaster)
