import time

import pytest
from flaky import flaky
from selenium.common.exceptions import ElementNotInteractableException, NoSuchElementException

from axonius.utils.wait import wait_until
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import (INCORRECT_PASSWORD, UNMATCHED_PASSWORD1, UNMATCHED_PASSWORD2,
                                      NEW_PASSWORD, RESTRICTED_USERNAME, FIRST_NAME, LAST_NAME)

PASSWORD_POLICY_ERROR_MSG = 'Password does not meet the password policy requirements'


class TestChangePasswordSettings(TestBase):

    PASSWORD_LENGTH_REQUIREMENT = 'Minimum {0} character{1}'
    PASSWORD_LOWERCASE_REQUIREMENT = '{0} lowercase letter{1}'
    PASSWORD_UPPERCASE_REQUIREMENT = '{0} uppercase letter{1}'
    PASSWORD_NUMBERS_REQUIREMENT = '{0} number{1}'
    PASSWORD_SPECIAL_REQUIREMENT = '{0} special character{1}'

    def test_change_password(self):
        self.account_page.switch_to_page()
        self.account_page.click_change_admin_password()

        # Fill in the current password
        assert self.account_page.is_save_button_disabled()
        self.account_page.fill_current_password(self.password)
        assert self.account_page.is_save_button_disabled()
        self.account_page.fill_new_password(self.password)
        assert self.account_page.is_save_button_disabled()
        self.account_page.fill_confirm_password(self.password)
        assert not self.account_page.is_save_button_disabled()
        self.account_page.click_save_button()
        self.account_page.wait_for_password_changed_toaster()

        # Fill in incorrect password
        self.account_page.change_password(INCORRECT_PASSWORD,
                                          INCORRECT_PASSWORD,
                                          INCORRECT_PASSWORD,
                                          self.account_page.wait_for_given_password_is_wrong_toaster)

        # Fill in unmacthed passwords
        self.account_page.change_password(self.password,
                                          UNMATCHED_PASSWORD1,
                                          UNMATCHED_PASSWORD2,
                                          self.account_page.wait_for_passwords_dont_match_toaster)

        # Fill in new password
        self.account_page.change_password(self.password,
                                          NEW_PASSWORD,
                                          NEW_PASSWORD,
                                          self.account_page.wait_for_password_changed_toaster)

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=self.username, password=INCORRECT_PASSWORD)
        assert self.login_page.wait_for_invalid_login_message()
        self.login_page.login(username=self.username, password=UNMATCHED_PASSWORD1)
        assert self.login_page.wait_for_invalid_login_message()
        self.login_page.login(username=self.username, password=UNMATCHED_PASSWORD2)
        assert self.login_page.wait_for_invalid_login_message()
        self.account_page.refresh()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=self.username, password=NEW_PASSWORD)

        self.account_page.switch_to_page()

        # Change password back
        self.account_page.change_password(NEW_PASSWORD,
                                          self.password,
                                          self.password,
                                          self.account_page.wait_for_password_changed_toaster)

    def test_password_policy(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.set_password_policy_toggle(True)
        self.settings_page.fill_password_policy(password_length=5, min_lowercase=2, min_uppercase=3,
                                                min_special_chars=1, min_numbers=2)
        # Make sure the validation work as it should
        with pytest.raises(ElementNotInteractableException):
            self.settings_page.click_save_global_settings()

        self.settings_page.fill_password_policy(password_length=10, min_lowercase=2, min_uppercase=3,
                                                min_special_chars=1, min_numbers=2)
        self.settings_page.click_save_global_settings()

        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(RESTRICTED_USERNAME,
                                           NEW_PASSWORD,
                                           FIRST_NAME,
                                           LAST_NAME,
                                           self.settings_page.RESTRICTED_ROLE,
                                           wait_for_toaster=False, wait_for_side_panel_absence=False)

        self.settings_page.assert_server_error(PASSWORD_POLICY_ERROR_MSG)

        self.settings_page.close_user_panel()
        self.settings_page.safe_refresh()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(RESTRICTED_USERNAME,
                                           'aaaBBB!123123',
                                           FIRST_NAME,
                                           LAST_NAME,
                                           self.settings_page.RESTRICTED_ROLE)
        self.settings_page.click_edit_user(RESTRICTED_USERNAME)
        self.settings_page.fill_password_field('kjfsk8978')
        self.settings_page.click_save_button()
        self.settings_page.assert_server_error(PASSWORD_POLICY_ERROR_MSG)
        self.settings_page.close_user_panel()

        self.settings_page.safe_refresh()
        self.settings_page.click_manage_users_settings()

        self.account_page.switch_to_page()
        self.account_page.click_change_admin_password()
        self.account_page.fill_current_password(self.password)
        self.account_page.fill_new_password('aaabbb43')
        self.account_page.fill_confirm_password('aaabbb43')
        self.account_page.click_save_button()
        assert wait_until(self.account_page.get_user_dialog_error,
                          tolerated_exceptions_list=[NoSuchElementException]) == PASSWORD_POLICY_ERROR_MSG
        self.settings_page.restore_initial_password_policy()

    @flaky(max_runs=2)
    def test_gui_restart_keeps_password(self):
        self.account_page.switch_to_page()
        self.account_page.click_change_admin_password()

        # Fill in new password
        self.account_page.change_password(self.password,
                                          NEW_PASSWORD,
                                          NEW_PASSWORD,
                                          self.account_page.wait_for_password_changed_toaster)

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()

        gui_service = self.axonius_system.gui
        gui_service.take_process_ownership()
        gui_service.stop(should_delete=False)
        gui_service.start_and_wait()
        time.sleep(5)

        # Check that we can log in with the new password
        self.account_page.refresh()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=self.username, password=NEW_PASSWORD)
        self.account_page.switch_to_page()

        # Change password back
        self.account_page.change_password(NEW_PASSWORD,
                                          self.password,
                                          self.password,
                                          self.account_page.wait_for_password_changed_toaster)

    def _switch_to_change_password_page(self):
        reset_password_link = self.settings_page.create_and_get_reset_password_link()
        self.settings_page.close_reset_password_modal()
        self.login_page.logout()
        self.reset_password_page.load_reset_password_link(reset_password_link)

    def _set_password_policy_and_verify_appearance(self, length: int,
                                                   lowercase: int = 0, uppercase: int = 0,
                                                   numbers: int = 0, special_chars: int = 0):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.set_password_policy_toggle(True)
        self.settings_page.fill_password_policy(length, lowercase, uppercase, numbers, special_chars)
        self.settings_page.click_save_global_settings()
        self.settings_page.wait_for_saved_successfully_toaster()

        def _format_requirement(requirement_template, value):
            return requirement_template.format(value, 's' if value > 1 else '')

        expected_requirements_list = [_format_requirement(template, value)
                                      for (template, value) in [(self.PASSWORD_LENGTH_REQUIREMENT, length),
                                                                (self.PASSWORD_LOWERCASE_REQUIREMENT, lowercase),
                                                                (self.PASSWORD_UPPERCASE_REQUIREMENT, uppercase),
                                                                (self.PASSWORD_NUMBERS_REQUIREMENT, numbers),
                                                                (self.PASSWORD_SPECIAL_REQUIREMENT, special_chars)]
                                      if value]
        self.settings_page.click_manage_users_settings()
        self.settings_page.wait_for_table_to_be_responsive()
        self.settings_page.click_new_user()
        assert self.settings_page.get_password_policy_requirements_list() == expected_requirements_list

        self.settings_page.close_user_panel()
        self.settings_page.click_edit_user(self.username)
        assert self.settings_page.get_password_policy_requirements_list() == expected_requirements_list

        self._switch_to_change_password_page()
        assert self.reset_password_page.get_password_policy_requirements_list() == expected_requirements_list
        self.login()

        self.account_page.switch_to_page()
        self.account_page.click_change_admin_password()
        assert self.account_page.get_password_policy_requirements_list() == expected_requirements_list

    def test_password_policy_user_indication(self):
        """
        Password Policy requirements, if configured, should be stated to the user in the locations:
         My Account -> Password
         Settings -> Manage Users -> Add User / Edit existing
         Change Password

        :return:
        """
        # Initially password policy is not enabled and requirements not expected at all

        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.wait_for_table_to_be_responsive()
        self.settings_page.click_new_user()
        with pytest.raises(NoSuchElementException):
            self.settings_page.find_password_policy_requirements()

        self.settings_page.close_user_panel()
        self.settings_page.click_edit_user(self.username)
        with pytest.raises(NoSuchElementException):
            self.settings_page.find_password_policy_requirements()

        self._switch_to_change_password_page()
        with pytest.raises(NoSuchElementException):
            self.settings_page.find_password_policy_requirements()
        self.login()

        self.account_page.switch_to_page()
        self.account_page.click_change_admin_password()
        with pytest.raises(NoSuchElementException):
            self.account_page.find_password_policy_requirements()

        # Once password policy is enabled, matching requirements are expected in all locations
        self._set_password_policy_and_verify_appearance(8, 1, 3, 2, 1)
        self._set_password_policy_and_verify_appearance(5, 0, 1, 1, 0)

        self.settings_page.restore_initial_password_policy()
