from axonius.consts.gui_consts import PREDEFINED_ROLE_VIEWER, PREDEFINED_ROLE_NO_ACCESS
from test_credentials.test_okta_credentials import OKTA_LOGIN_DETAILS, OKTA_CLIENT_LOGIN_DETAILS
from ui_tests.tests import hosts_file_modifier
from ui_tests.tests.ui_test_base import TestBase


class TestSamlAutoRedirect(TestBase):
    REDIRECT_PARAM = 'redirect=false'

    def test_saml_auto_redirect(self):
        self._add_saml_and_login(new_user_role=PREDEFINED_ROLE_VIEWER)
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()

        self.login_page.login(self.username, self.password)
        self.settings_page.set_saml_auto_redirect()

        # refresh global settings fetch, for adding redirect=false param to the logout redirection
        # preventing a login loop with the auto login feature
        self.settings_page.hard_refresh()
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        assert self.REDIRECT_PARAM in self.driver.current_url

        # remove the parm and wait for the auto redirect to gets us logged in
        self.driver.get(self.base_url)
        self.dashboard_page.wait_for_trial_banner()
        self.login_page.logout()

        self.login_page.login(self.username, self.password)
        self.settings_page.set_saml_auto_redirect(False)
        self.settings_page.hard_refresh()
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        assert self.REDIRECT_PARAM not in self.driver.current_url
        self.login_page.click_login_with_saml()
        self.dashboard_page.wait_for_trial_banner()

    def test_saml_auto_redirect_permission_loop_prevented(self):
        self._add_saml_and_login(new_user_role=PREDEFINED_ROLE_NO_ACCESS)
        self.login_page.assert_login_permission_error_message()

    def _add_saml_and_login(self, new_user_role=None):
        self.settings_page.set_saml(OKTA_LOGIN_DETAILS['name'],
                                    OKTA_LOGIN_DETAILS['meta_data_url'],
                                    '',
                                    new_user_role)
        self.dashboard_page.switch_to_page()
        hosts_file_modifier.HostsFileModifier.add_url_if_not_exist('127.0.0.1',
                                                                   self.login_page.OKTA_URL)
        self.change_base_url(f'https://{self.login_page.OKTA_URL}:{self.port}')
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login_with_okta_server(OKTA_CLIENT_LOGIN_DETAILS)
