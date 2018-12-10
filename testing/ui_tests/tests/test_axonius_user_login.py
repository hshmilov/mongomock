import re
from axonius.utils.wait import wait_until
from test_credentials.test_gui_credentials import AXONIUS_USER
from ui_tests.tests.ui_test_base import TestBase


class TestAxoniusUserLogin(TestBase):
    def test_axoniususer_login(self):
        self.settings_page.switch_to_page()
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()

        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])

        tester = self.axonius_system.gui.log_tester
        wait_until(lambda: tester.is_pattern_in_log(re.escape('"metric_name": "LOGIN_MARKER"'), 20))
        wait_until(lambda: tester.is_pattern_in_log(re.escape('"ui_user": "admin", "ui_user_source": "internal"'), 20))
        wait_until(lambda: tester.is_metric_in_log(metric_name='LOGIN_MARKER', value=0, lines_lookback=20))

        # So we can see that we're in
        self.settings_page.switch_to_page()
