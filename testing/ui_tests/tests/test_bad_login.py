from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests import ui_consts


class TestBadLogin(TestBase):
    def test_bad_login(self):
        self.settings_page.switch_to_page()
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()

        self.login_page.login(username=ui_consts.BAD_USERNAME, password=self.password)
        assert self.login_page.wait_for_invalid_login_message()
        self.login_page.login(username=self.username, password=ui_consts.BAD_PASSWORD)
        assert self.login_page.wait_for_invalid_login_message()
        self.login_page.fill_username('')
        self.login_page.fill_password('')
        assert self.login_page.find_disabled_login_button()
        self.login_page.login(username=f'{self.username}\'', password=f'{self.password}\'')
        assert self.login_page.wait_for_invalid_login_message()

        self.settings_page.refresh()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=self.username, password=self.password)

        # So we can see that we're in
        self.settings_page.switch_to_page()
