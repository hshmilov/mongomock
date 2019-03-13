from ui_tests.tests.ui_test_base import TestBase
from test_credentials.test_ad_credentials import ad_client1_details


class TestLDAPLogin(TestBase):
    def test_ldap_login(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_gui_settings()
        self.settings_page.wait_for_spinner_to_end()
        toggle = self.settings_page.find_allow_ldap_logins_toggle()
        self.settings_page.click_toggle_button(toggle, scroll_to_toggle=False)
        self.settings_page.fill_dc_address(ad_client1_details['dc_name'])
        self.settings_page.click_save_button()
        self.settings_page.find_saved_successfully_toaster()

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.click_login_with_ldap()
        self.login_page.wait_for_spinner_to_end()
        domain, username = ad_client1_details['user'].split('\\')

        self.login_page.fill_ldap_login_details(username=username + 'bad',
                                                password=ad_client1_details['password'],
                                                domain=domain)
        self.login_page.click_login_button()
        assert self.login_page.find_failed_ad_login_msg()

        self.login_page.fill_ldap_login_details(username=username,
                                                password=ad_client1_details['password'],
                                                domain=domain)
        self.login_page.click_login_button()

        # Making sure we are indeed logged in
        self.settings_page.switch_to_page()

        for screen in self.get_all_screens():
            screen.assert_screen_is_restricted()
