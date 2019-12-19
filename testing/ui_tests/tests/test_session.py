import time

from ui_tests.tests.ui_test_base import TestBase


class TestSession(TestBase):
    TIMEOUT_IN_MINUTES = 2

    def test_session_timeout_on_no_use(self):
        self.settings_page.switch_to_page()
        self.settings_page.set_session_timeout(True, self.TIMEOUT_IN_MINUTES)

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()

        self.login(False)

        self.dashboard_page.switch_to_page()

        self.login_page.assert_logged_in()

        # wait until session should end
        time.sleep((self.TIMEOUT_IN_MINUTES * 60) + 20)

        self.login_page.assert_not_logged_in()

    def test_session_resumes_if_in_use(self):
        self.settings_page.switch_to_page()
        self.settings_page.set_session_timeout(True, self.TIMEOUT_IN_MINUTES)
        self.base_page.run_discovery()

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()

        self.login(False)

        self.dashboard_page.switch_to_page()

        self.login_page.assert_logged_in()

        # wait for half of the session duration
        time.sleep((self.TIMEOUT_IN_MINUTES / 2) * 60)
        self.login_page.assert_logged_in()

        self.dashboard_page.find_space_header(2).click()

        # wait for the next half  and 20 seconds more then session duration - from the session beginning
        time.sleep((self.TIMEOUT_IN_MINUTES / 2) * 60 + 20)
        self.login_page.assert_logged_in()

        self.dashboard_page.find_space_header(1).click()

        # wait until session should end
        time.sleep((self.TIMEOUT_IN_MINUTES * 60) + 20)

        self.login_page.assert_not_logged_in()

    def test_multiple_tabs(self):
        self.settings_page.switch_to_page()
        self.settings_page.set_session_timeout(True, self.TIMEOUT_IN_MINUTES)

        self.dashboard_page.switch_to_page()

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()

        self.login(False)

        first_tab = self.settings_page.get_current_window()

        self.settings_page.switch_to_page()

        second_tab = self.settings_page.open_new_tab()

        self.settings_page.switch_tab(second_tab)

        self.reports_page.switch_to_page()

        # Wait for half of the timeout time
        time.sleep(self.TIMEOUT_IN_MINUTES * 60 / 2)

        # switch a page in order to mimic a renew of the session
        self.settings_page.switch_to_page()

        # Wait for half a minute more then half the timeout time (check that the renew of the session works)
        time.sleep(self.TIMEOUT_IN_MINUTES * 60 / 2 + 30)

        self.settings_page.switch_tab(first_tab)

        self.login_page.assert_logged_in()

        # Wait for half a minute more then the timeout time (check that the session timed out)
        time.sleep(self.TIMEOUT_IN_MINUTES * 60 + 30)

        self.login_page.assert_not_logged_in()

        assert self.login_page.get_error_msg() == 'Session timed out'

        time.sleep(20)

        self.settings_page.switch_tab(second_tab)

        self.login_page.assert_not_logged_in()
