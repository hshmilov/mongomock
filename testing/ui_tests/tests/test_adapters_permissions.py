from axonius.utils.wait import wait_until
from ui_tests.tests import ui_consts
from ui_tests.tests.permissions_test_base import PermissionsTestBase
from ui_tests.tests.ui_consts import JSON_ADAPTER_NAME

# pylint: disable=no-member


class TestAdaptersPermissions(PermissionsTestBase):

    def test_adapters_permissions(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        self.settings_page.wait_for_table_to_load()
        settings_permissions = {
            'adapters': [
                'View adapters'
            ]
        }
        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.switch_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.adapters_page.switch_to_page()
        self.adapters_page.click_adapter(JSON_ADAPTER_NAME)
        self.adapters_page.assert_new_server_button_is_disabled()
        self.adapters_page.assert_advanced_settings_is_disabled()
        assert self.adapters_page.is_row_checkbox_absent()
        self.adapters_page.assert_servers_cant_be_opened()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'adapters',
                                                     'Add connection',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self.adapters_page.switch_to_page()
        self.adapters_page.add_json_extra_client()
        assert self.adapters_page.is_row_checkbox_absent()
        self.adapters_page.assert_servers_cant_be_opened()
        self.adapters_page.assert_advanced_settings_is_disabled()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'adapters',
                                                     'Edit connections',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self.adapters_page.switch_to_page()
        self.adapters_page.click_adapter(JSON_ADAPTER_NAME)
        self.adapters_page.assert_new_server_button_is_enabled()
        assert self.adapters_page.is_row_checkbox_absent()
        self.adapters_page.assert_advanced_settings_is_disabled()
        self.adapters_page.click_edit_server()
        self.adapters_page.click_save()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'adapters',
                                                     'Edit adapter advanced settings',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self.adapters_page.switch_to_page()
        self.adapters_page.click_adapter(JSON_ADAPTER_NAME)
        self.adapters_page.assert_new_server_button_is_enabled()
        self.adapters_page.assert_advanced_settings_is_enabled()
        assert self.adapters_page.is_row_checkbox_absent()
        self.adapters_page.click_edit_server()
        wait_until(lambda: not self.adapters_page.is_save_button_disabled())
        self.adapters_page.click_save()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'adapters',
                                                     'Delete connection',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self.adapters_page.switch_to_page()
        self.adapters_page.click_adapter(JSON_ADAPTER_NAME)
        self.adapters_page.assert_new_server_button_is_enabled()
        self.adapters_page.assert_advanced_settings_is_enabled()
        assert not self.adapters_page.is_row_checkbox_absent()
        self.adapters_page.click_edit_server()
        wait_until(lambda: not self.adapters_page.is_save_button_disabled())
        self.adapters_page.click_save()
