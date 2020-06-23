import pytest
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from ui_tests.tests import ui_consts
from ui_tests.tests.permissions_test_base import PermissionsTestBase


# pylint: disable=no-member


class TestSettingsPermissions(PermissionsTestBase):

    def test_settings_users_permissions(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        self.login_page.switch_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        self.settings_page.assert_screen_is_restricted()
        self.login_page.logout_and_login_with_admin()
        self.settings_page.switch_to_page()
        settings_permissions = {'settings': []}
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'View system settings',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        self.settings_page.switch_to_page()
        assert not self.settings_page.is_users_and_roles_enabled()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'View user accounts and roles',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.settings_page.switch_to_page()
        assert self.settings_page.is_users_and_roles_enabled()
        self.settings_page.click_manage_users_settings()
        self.settings_page.assert_new_user_disabled()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'Add user',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        new_user = 'test_user'
        self.settings_page.create_new_user(new_user,
                                           ui_consts.NEW_PASSWORD,
                                           new_user,
                                           new_user,
                                           self.settings_page.RESTRICTED_ROLE)
        # Checking the user can't click on any row
        assert len(self.settings_page.get_all_table_rows(clickable_rows=True)) == 0
        # Checking user can not be deleted
        self.settings_page.is_row_checkbox_absent(2)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'Edit users',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.click_edit_user(new_user)
        self.settings_page.assert_user_remove_button_missing()
        self.settings_page.click_save_button()
        self.settings_page.wait_for_user_updated_toaster()

        update_user = 'update user'
        self.settings_page.update_new_user(new_user,
                                           ui_consts.UPDATE_PASSWORD,
                                           update_user,
                                           update_user,
                                           self.settings_page.VIEWER_ROLE)
        self.settings_page.wait_for_table_to_load()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'Delete user',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        self.settings_page.remove_user_by_user_name_with_selection(new_user)

        self.settings_page.create_new_user(new_user,
                                           ui_consts.NEW_PASSWORD,
                                           new_user,
                                           new_user,
                                           self.settings_page.RESTRICTED_ROLE)

        self.settings_page.remove_user_by_user_name_with_user_panel(new_user)

    def test_settings_roles_permissions(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        self.settings_page.switch_to_page()

        settings_permissions = {'settings': []}
        settings_permissions['settings'].append('View system settings')
        settings_permissions['settings'].append('View user accounts and roles')

        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.switch_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.settings_page.switch_to_page()
        assert self.settings_page.is_users_and_roles_enabled()
        self.settings_page.click_manage_roles_settings()
        self.settings_page.assert_new_role_disabled()
        self.settings_page.click_role_by_name(user_role)
        with pytest.raises(NoSuchElementException):
            self.settings_page.get_save_button()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'Edit roles',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_settings_roles_with_edit_permission(user_role)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'Add role',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        new_role_name = self._test_settings_roles_with_add_permission()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'Delete role',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_settings_roles_with_delete_permission(new_role_name)

    def _test_settings_roles_with_delete_permission(self, new_role_name):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_roles_settings()
        assert self.settings_page.get_new_role_enabled_button()
        self.settings_page.click_role_by_name(new_role_name)
        self.settings_page.wait_for_role_panel_present()
        self.settings_page.get_role_edit_panel_action().click()
        self.settings_page.click_save_button()
        self.settings_page.wait_for_role_panel_absent()
        self.settings_page.remove_role(new_role_name)

    def _test_settings_roles_with_add_permission(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_roles_settings()
        assert self.settings_page.get_new_role_enabled_button()
        self.settings_page.click_role_by_name(self.settings_page.RESTRICTED_ROLE)
        assert self.settings_page.get_role_duplicate_panel_action()
        self.settings_page.assert_role_remove_button_missing()
        self.settings_page.close_role_panel()
        new_role_name = 'new role'
        self.settings_page.create_new_role(new_role_name, self.settings_page.RESTRICTED_PERMISSIONS)
        self.settings_page.click_role_by_name(new_role_name)
        assert self.settings_page.get_role_duplicate_panel_action()
        self.settings_page.assert_role_remove_button_missing()
        self.settings_page.close_role_panel()
        return new_role_name

    def _test_settings_roles_with_edit_permission(self, user_role):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_roles_settings()
        self.settings_page.assert_new_role_disabled()
        self.settings_page.click_role_by_name(user_role)
        self.settings_page.wait_for_side_panel()
        with pytest.raises(TimeoutException):
            self.settings_page.get_role_duplicate_panel_action()
        with pytest.raises(TimeoutException):
            self.settings_page.get_role_remove_panel_action()
        self.settings_page.get_role_edit_panel_action().click()
        self.settings_page.click_save_button()
        self.settings_page.safeguard_click_confirm('Yes')
        self.login()

    def test_settings_general_permissions(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        self.settings_page.switch_to_page()

        settings_permissions = {'settings': []}
        settings_permissions['settings'].append('View system settings')
        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.switch_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        assert self.base_page.is_run_research_disabled()
        self.account_page.switch_to_page()
        assert not self.account_page.is_reset_key_displayed()
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'Reset API Key',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        assert self.base_page.is_run_research_disabled()
        self.account_page.switch_to_page()
        assert self.account_page.is_reset_key_displayed()
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'Run manual discovery cycle',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        assert not self.base_page.is_run_research_disabled()

        self.settings_page.switch_to_page()
        self.settings_page.click_lifecycle_settings()
        assert self.settings_page.is_save_button_disabled()
        self.settings_page.click_global_settings()
        assert self.settings_page.is_save_button_disabled()
        self.settings_page.click_gui_settings()
        assert self.settings_page.is_save_button_disabled()
        self.account_page.switch_to_page()
        assert self.account_page.is_reset_key_displayed()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'settings',
                                                     'Update system settings',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self.settings_page.switch_to_page()
        self.settings_page.click_lifecycle_settings()
        assert not self.settings_page.is_save_button_disabled()
        self.settings_page.click_global_settings()
        assert not self.settings_page.is_save_button_disabled()
        self.settings_page.click_gui_settings()
        assert not self.settings_page.is_save_button_disabled()
        self.account_page.switch_to_page()
        assert self.account_page.is_reset_key_displayed()
        assert not self.base_page.is_run_research_disabled()
