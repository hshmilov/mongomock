from axonius.consts.plugin_consts import AXONIUS_USER_NAME
from ui_tests.tests.ui_test_base import TestBase


class TestManageUsersSettings(TestBase):
    def test_remote_control_user_hidden(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        usernames = list(self.settings_page.get_all_users_from_users_and_roles())
        assert 'admin' in usernames
        assert AXONIUS_USER_NAME not in usernames
