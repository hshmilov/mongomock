from ui_tests.tests.ui_test_base import TestBase

INCORRECT_PASSWORD = 'Incorrect!'
UNMATCHED_PASSWORD1 = 'Unmatched!'
UNMATCHED_PASSWORD2 = 'Unmatched!2'


class TestChangePasswordSettings(TestBase):
    def test_change_password(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_change_admin_password()

        # Fill in correct details
        assert not self.settings_page.is_save_button_enabled()
        self.settings_page.fill_current_password(self.password)
        assert not self.settings_page.is_save_button_enabled()
        self.settings_page.fill_new_password(self.password)
        assert not self.settings_page.is_save_button_enabled()
        self.settings_page.fill_confirm_password(self.password)
        assert self.settings_page.is_save_button_enabled()
        self.settings_page.click_save_button()
        self.settings_page.wait_for_password_changed_toaster()

        # Fill incorrect password
        self.settings_page.refresh()
        self.settings_page.click_change_admin_password()
        self.settings_page.fill_current_password(INCORRECT_PASSWORD)
        self.settings_page.fill_new_password(INCORRECT_PASSWORD)
        self.settings_page.fill_confirm_password(INCORRECT_PASSWORD)
        self.settings_page.click_save_button()
        self.settings_page.wait_for_given_password_is_wrong_toaster()

        # Fill unmacthed passwords
        self.settings_page.refresh()
        self.settings_page.click_change_admin_password()
        self.settings_page.fill_current_password(self.password)
        self.settings_page.fill_new_password(UNMATCHED_PASSWORD1)
        self.settings_page.fill_confirm_password(UNMATCHED_PASSWORD2)
        self.settings_page.click_save_button()
        self.settings_page.wait_for_passwords_dont_match_toaster()

        # Logout and test that password isn't changed
        # Missing: change passwords for real and see that I can log in with them
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=self.username, password=INCORRECT_PASSWORD)
        assert self.login_page.wait_for_invalid_login_message()
        self.login_page.login(username=self.username, password=UNMATCHED_PASSWORD1)
        assert self.login_page.wait_for_invalid_login_message()
        self.login_page.login(username=self.username, password=UNMATCHED_PASSWORD2)
        assert self.login_page.wait_for_invalid_login_message()
        self.login_page.login(username=self.username, password=self.password)
