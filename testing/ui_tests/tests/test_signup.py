from axonius.consts.gui_consts import (Signup, SIGNUP_TEST_COMPANY_NAME)
from ui_tests.tests.ui_consts import LOGGED_IN_MARKER
from ui_tests.tests.ui_test_base import TestBase


class TestSignup(TestBase):

    def restore_pre_signup_state(self):
        if LOGGED_IN_MARKER.is_file():
            LOGGED_IN_MARKER.unlink()
        self.axonius_system.gui.get_signup_collection().drop()

    def test_signup(self):
        self.settings_page.switch_to_page()
        self.login_page.logout()
        self.restore_pre_signup_state()
        self.login_page.refresh()
        self.signup_page.wait_for_signup_page_to_load()

        company_name = SIGNUP_TEST_COMPANY_NAME

        self.signup_page.fill_signup_and_save(company=company_name, email='a@b', passw='1', confirm_passw='2')
        self.signup_page.wait_for_passwords_dont_match_error()

        self.signup_page.fill_signup_and_save(company=company_name, email='a@b', passw='123', confirm_passw='123')
        self.login_page.wait_for_login_page_to_load()

        signup_data = self.axonius_system.gui.get_signup_collection().find_one()
        # if this one changes - we might need to update integration with chef
        assert signup_data[Signup.CompanyField] == company_name

        self.login_page.login(username='admin', password='123')
        self.dashboard_page.find_trial_remainder_banner(30)
        self.settings_page.switch_to_page()

        self.login_page.logout()
        self.restore_pre_signup_state()
        self.login_page.refresh()
        self.signup_page.fill_signup_with_defaults_and_save()
