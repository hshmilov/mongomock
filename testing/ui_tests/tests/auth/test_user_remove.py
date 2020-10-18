from axonius.consts.gui_consts import PREDEFINED_ROLE_RESTRICTED
from ui_tests.tests.test_api import get_device_views_from_api
from ui_tests.tests.ui_consts import (LAST_NAME, FIRST_NAME, NEW_PASSWORD, UPDATE_USERNAME)
from ui_tests.tests.ui_test_base import TestBase


class TestUserRemove(TestBase):

    def test_remove_revokes_access(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(UPDATE_USERNAME, NEW_PASSWORD, FIRST_NAME, LAST_NAME,
                                           PREDEFINED_ROLE_RESTRICTED)

        # Get API access data
        self.login_page.switch_user(UPDATE_USERNAME, NEW_PASSWORD)
        self.account_page.switch_to_page()
        account_data = self.account_page.get_api_key_and_secret()

        # Remove the new user
        self.login_page.switch_user(self.username, self.password)
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.remove_user_by_user_name_with_user_panel(UPDATE_USERNAME)

        # Verify removed user cannot login
        self.login_page.logout()
        self.login_page.login(UPDATE_USERNAME, NEW_PASSWORD)
        assert self.login_page.wait_for_invalid_login_message()

        # Verify removed user cannot use API
        assert get_device_views_from_api(account_data).status_code == 401
