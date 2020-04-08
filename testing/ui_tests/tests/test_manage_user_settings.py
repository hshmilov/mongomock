from axonius.consts.plugin_consts import AXONIUS_USERS_LIST
from ui_tests.tests.ui_test_base import TestBase


class TestManageUsersSettings(TestBase):
    def test_remote_control_user_hidden(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        usernames = list(self.settings_page.get_all_user_names())
        assert 'admin' in usernames
        for user in AXONIUS_USERS_LIST:
            assert user not in usernames
