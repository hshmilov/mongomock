from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests import ui_consts


class TestChangePasswordSettings(TestBase):
    def test_change_password(self):
        self.my_account_page.switch_to_page()
        self.my_account_page.click_change_admin_password()

        # Fill in the current password
        assert not self.my_account_page.is_save_button_enabled()
        self.my_account_page.fill_current_password(self.password)
        assert not self.my_account_page.is_save_button_enabled()
        self.my_account_page.fill_new_password(self.password)
        assert not self.my_account_page.is_save_button_enabled()
        self.my_account_page.fill_confirm_password(self.password)
        assert self.my_account_page.is_save_button_enabled()
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

    def _change_password(self, current, new1, new2, wait_for=None):
        self.my_account_page.click_change_admin_password()
        self.my_account_page.fill_current_password(current)
        self.my_account_page.fill_new_password(new1)
        self.my_account_page.fill_confirm_password(new2)
        self.my_account_page.click_save_button()
        if wait_for:
            wait_for()
