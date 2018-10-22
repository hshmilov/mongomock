from test_credentials.test_gui_credentials import AXONIUS_USER
from ui_tests.tests.ui_test_base import TestBase


class TestAxoniusUserLogin(TestBase):
    def test_axoniususer_login(self):
        self.settings_page.switch_to_page()
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()

        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])

        # So we can see that we're in
        self.settings_page.switch_to_page()
