from ui_tests.tests.ui_test_base import TestBase

INCORRECT_PASSWORD = 'Incorrect!'
UNMATCHED_PASSWORD1 = 'Unmatched!'
UNMATCHED_PASSWORD2 = 'Unmatched!2'
NEW_PASSWORD = 'NewPassword!'


class TestChangePasswordSettings(TestBase):
    def test_change_password(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_change_admin_password()

        # Fill in the current password
        assert not self.settings_page.is_save_button_enabled()
        self.settings_page.fill_current_password(self.password)
        assert not self.settings_page.is_save_button_enabled()
        self.settings_page.fill_new_password(self.password)
        assert not self.settings_page.is_save_button_enabled()
        self.settings_page.fill_confirm_password(self.password)
        assert self.settings_page.is_save_button_enabled()
        self.settings_page.click_save_button()
        self.settings_page.wait_for_password_changed_toaster()

        # Fill in incorrect password
        self._change_password(INCORRECT_PASSWORD,
                              INCORRECT_PASSWORD,
                              INCORRECT_PASSWORD,
                              self.settings_page.wait_for_given_password_is_wrong_toaster)

        # Fill in unmacthed passwords
        self._change_password(self.password,
                              UNMATCHED_PASSWORD1,
                              UNMATCHED_PASSWORD2,
                              self.settings_page.wait_for_passwords_dont_match_toaster)

        # Fill in new password
        self._change_password(self.password,
                              NEW_PASSWORD,
                              NEW_PASSWORD,
                              self.settings_page.wait_for_password_changed_toaster)

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=self.username, password=INCORRECT_PASSWORD)
        assert self.login_page.wait_for_invalid_login_message()
        self.login_page.login(username=self.username, password=UNMATCHED_PASSWORD1)
        assert self.login_page.wait_for_invalid_login_message()
        self.login_page.login(username=self.username, password=UNMATCHED_PASSWORD2)
        assert self.login_page.wait_for_invalid_login_message()
        self.settings_page.refresh()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=self.username, password=NEW_PASSWORD)

        self.settings_page.switch_to_page()

        # Change password back
        self._change_password(NEW_PASSWORD,
                              self.password,
                              self.password,
                              self.settings_page.wait_for_password_changed_toaster)

    def _change_password(self, current, new1, new2, wait_for=None):
        self.settings_page.refresh()
        self.settings_page.click_change_admin_password()
        self.settings_page.fill_current_password(current)
        self.settings_page.fill_new_password(new1)
        self.settings_page.fill_confirm_password(new2)
        self.settings_page.click_save_button()
        if wait_for:
            wait_for()
