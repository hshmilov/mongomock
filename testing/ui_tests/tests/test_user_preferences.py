from ui_tests.tests.ui_consts import FIRST_NAME, READ_ONLY_USERNAME, NEW_PASSWORD, LAST_NAME
from ui_tests.tests.ui_test_base import TestBase


class TestUserPreferences(TestBase):

    @staticmethod
    def _assert_fields_match(entities_page, fields_list):
        entities_page.wait_for_table_to_be_responsive()
        assert entities_page.get_columns_header_text() == fields_list

    def _test_system_default_view(self, entities_page, field_to_add):
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_be_responsive()
        assert entities_page.get_columns_header_text() == entities_page.SYSTEM_DEFAULT_FIELDS
        entities_page.edit_columns([field_to_add])
        assert entities_page.get_columns_header_text()[-1] == field_to_add
        entities_page.reset_columns_system_default()
        self._assert_fields_match(entities_page, entities_page.SYSTEM_DEFAULT_FIELDS)

    def test_system_default_view(self):
        self._test_system_default_view(self.devices_page, self.devices_page.FIELD_LAST_USED_USERS)
        self._test_system_default_view(self.users_page, self.users_page.FIELD_LOGON_COUNT)

    def _test_view_after_refresh(self, entities_page, fields_list):
        entities_page.refresh()
        self._assert_fields_match(entities_page, fields_list)

    def _test_view_after_navigation(self, entities_page, fields_list):
        self.dashboard_page.switch_to_page()
        entities_page.switch_to_page()
        self._assert_fields_match(entities_page, fields_list)

    def _test_view_after_login(self, entities_page, fields_list):
        entities_page.reset_columns_system_default()
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(self.username, self.password)
        entities_page.switch_to_page()
        self._assert_fields_match(entities_page, fields_list)

    def _test_view_after_switch_user(self, entities_page, fields_list):
        self.login_page.switch_user(READ_ONLY_USERNAME, NEW_PASSWORD)
        entities_page.switch_to_page()
        self._assert_fields_match(entities_page, fields_list)

    def _test_save_default_view(self, entities_page, fields_list):
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_be_responsive()
        entities_page.open_edit_columns()
        entities_page.remove_columns(entities_page.SYSTEM_DEFAULT_FIELDS)
        entities_page.add_columns(fields_list)
        entities_page.close_edit_columns_save_default()
        self._assert_fields_match(entities_page, fields_list)

        self._test_view_after_refresh(entities_page, fields_list)
        self._test_view_after_navigation(entities_page, fields_list)
        self._test_view_after_switch_user(entities_page, entities_page.SYSTEM_DEFAULT_FIELDS)
        self._test_view_after_login(entities_page, fields_list)

    def test_save_default_view(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(READ_ONLY_USERNAME, NEW_PASSWORD,
                                           FIRST_NAME, LAST_NAME, self.settings_page.READ_ONLY_ROLE)
        self.settings_page.wait_for_user_created_toaster()
        self._test_save_default_view(self.devices_page,
                                     [self.devices_page.FIELD_ADAPTERS, self.devices_page.FIELD_HOSTNAME_TITLE])
        self._test_save_default_view(self.users_page,
                                     [self.users_page.FIELD_ADAPTERS, self.users_page.FIELD_USERNAME_TITLE])
