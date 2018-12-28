import shlex
import subprocess
import sys

from test_credentials.test_okta_credentials import (OKTA_CLIENT_LOGIN_DETAILS,
                                                    OKTA_LOGIN_DETAILS)
from testing.services.weave_service import is_weave_up
from axonius.consts.plugin_consts import WEAVE_PATH
from ui_tests.tests import hosts_file_modifier
from ui_tests.tests.ui_test_base import TestBase


class TestOktaLogin(TestBase):
    def test_okta_login(self):
        if 'linux' in sys.platform.lower() and is_weave_up():
            cmd = f'{WEAVE_PATH} dns-add gui -h okta.axonius.local'
            subprocess.check_call(shlex.split(cmd))

        self.settings_page.switch_to_page()
        self.settings_page.click_gui_settings()
        self.settings_page.wait_for_spinner_to_end()
        toggle = self.settings_page.find_allow_okta_logins_toggle()
        self.settings_page.click_toggle_button(toggle)
        self.settings_page.fill_okta_login_details(**OKTA_LOGIN_DETAILS)
        self.settings_page.click_save_button()
        self.login_page.logout()
        # To support running with local browser
        hosts_file_modifier.HostsFileModifier.add_url_if_not_exist('127.0.0.1',
                                                                   self.login_page.OKTA_URL)

        try:
            self.change_base_url(f'https://{self.login_page.OKTA_URL}')
            self.login_page.wait_for_login_page_to_load()
            self.login_page.click_login_with_okta()
            self.login_page.fill_okta_client_login_details(OKTA_CLIENT_LOGIN_DETAILS)
            self.driver.find_element_by_id(self.login_page.OKTA_SUBMIT_BUTTON_ID).click()
            self.login_page.wait_for_spinner_to_end()
            # There is sometimes a bug where you need to press "Login with Okta".
            # If it happens to you locally, add self.login_page.click_login_with_okta() here.
            self.login_page.logout()
        finally:
            self.change_base_url(self.base_url)
