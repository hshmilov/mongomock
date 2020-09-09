from axonius.consts.gui_consts import PREDEFINED_ROLE_VIEWER
from test_credentials.test_okta_credentials import (OKTA_CLIENT_LOGIN_DETAILS,
                                                    OKTA_LOGIN_DETAILS)
from ui_tests.tests import hosts_file_modifier
from ui_tests.tests.permissions_test_base import PermissionsTestBase


class TestOktaLogin(PermissionsTestBase):
    def test_okta_user_added(self):
        self.base_page.run_discovery(False)
        self.settings_page.set_saml(OKTA_LOGIN_DETAILS['name'],
                                    OKTA_LOGIN_DETAILS['meta_data_url'],
                                    '',
                                    PREDEFINED_ROLE_VIEWER)
        self.dashboard_page.switch_to_page()
        hosts_file_modifier.HostsFileModifier.add_url_if_not_exist('127.0.0.1',
                                                                   self.login_page.OKTA_URL)
        self.change_base_url(f'https://{self.login_page.OKTA_URL}:{self.port}')
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login_with_okta_server(OKTA_CLIENT_LOGIN_DETAILS)
        self._assert_viewer_role()

        self.login_page.logout()
        self.change_base_url(self.base_url)
