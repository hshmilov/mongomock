from ui_tests.tests import ui_consts
from ui_tests.tests.ui_test_base import TestBase

# pylint: disable=no-member


class TestUserRoles(TestBase):
    REPORT_SUBJECT = 'axonius read only report subject'
    DATA_QUERY = 'specific_data.data.name == regex(\' no\', \'i\')'

    TEST_REPORT_READ_ONLY_QUERY = 'query for read only test'
    TEST_REPORT_READ_ONLY_NAME = 'report name read only'

    def test_new_user_is_restricted(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(ui_consts.RESTRICTED_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME,
                                           self.settings_page.RESTRICTED_ROLE)

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=ui_consts.RESTRICTED_USERNAME, password=ui_consts.NEW_PASSWORD)
        for screen in self.get_all_screens():
            screen.assert_screen_is_restricted()
            self.login_page.assert_screen_url_is_restricted(screen)

        self.settings_page.assert_screen_is_restricted()
        self.login_page.assert_screen_url_is_restricted(self.settings_page)

    def test_user_roles(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_roles_settings()
        # Checking that the viewer and restricted roles has the right permissions
        assert self.settings_page.match_role_permissions(self.settings_page.VIEWER_ROLE,
                                                         self.settings_page.VIEWER_PERMISSIONS)

        assert self.settings_page.match_role_permissions(self.settings_page.RESTRICTED_ROLE,
                                                         self.settings_page.RESTRICTED_PERMISSIONS)
        self.settings_page.wait_for_table_to_load()
        role_name = 'lalala'
        self.settings_page.click_new_role()
        self.settings_page.wait_for_role_panel_present()
        self.settings_page.fill_role_name(role_name)
        self.settings_page.click_create_role()
        self.settings_page.wait_for_role_successfully_created_toaster()
        # test delete role is missing
        self.settings_page.click_role_by_name(self.settings_page.RESTRICTED_ROLE)
        self.settings_page.wait_for_role_panel_present()
        self.settings_page.assert_role_remove_button_missing()
        self.settings_page.close_role_panel()
        # test the default permissions are the same as a restricted role
        assert self.settings_page.match_role_permissions(role_name,
                                                         self.settings_page.RESTRICTED_PERMISSIONS)
        # test delete role
        self.settings_page.remove_role(role_name)

    def test_new_user_with_role(self):
        self._enter_user_management_and_create_restricted_user()
        user_data = self.settings_page.get_user_data_by_user_name(ui_consts.RESTRICTED_USERNAME)
        assert self.settings_page.RESTRICTED_ROLE in user_data
        self.settings_page.refresh()
        self.settings_page.click_manage_users_settings()
        user_data = self.settings_page.get_user_data_by_user_name(ui_consts.RESTRICTED_USERNAME)
        assert self.settings_page.RESTRICTED_ROLE in user_data

        self.settings_page.click_manage_roles_settings()
        self.settings_page.match_role_permissions(self.settings_page.RESTRICTED_ROLE,
                                                  self.settings_page.RESTRICTED_PERMISSIONS)

        self.settings_page.click_manage_users_settings()
        # Change to Read Only role, save the user and check permissions correct also after refresh
        self.settings_page.click_edit_user(ui_consts.RESTRICTED_USERNAME)
        self.settings_page.wait_for_new_user_panel()
        self.settings_page.select_role(self.settings_page.VIEWER_ROLE)
        self.settings_page.save_user_wait_done()
        user_data = self.settings_page.get_user_data_by_user_name(ui_consts.RESTRICTED_USERNAME)
        assert self.settings_page.VIEWER_ROLE in user_data

        self.settings_page.refresh()
        self.settings_page.click_manage_users_settings()
        user_data = self.settings_page.get_user_data_by_user_name(ui_consts.RESTRICTED_USERNAME)
        assert self.settings_page.VIEWER_ROLE in user_data

        self.settings_page.click_manage_roles_settings()
        self.settings_page.match_role_permissions(self.settings_page.VIEWER_ROLE,
                                                  self.settings_page.VIEWER_PERMISSIONS)

        self.settings_page.click_manage_users_settings()
        self.settings_page.remove_user_by_user_name_with_user_panel(ui_consts.RESTRICTED_USERNAME)
        # Create user with Read Only role and check permissions correct also after refresh
        self.settings_page.create_new_user(ui_consts.READ_ONLY_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME,
                                           self.settings_page.VIEWER_ROLE)
        self.settings_page.wait_for_user_created_toaster()
        user_data = self.settings_page.get_user_data_by_user_name(ui_consts.READ_ONLY_USERNAME)
        assert self.settings_page.VIEWER_ROLE in user_data
        self.settings_page.refresh()
        self.settings_page.click_manage_users_settings()
        user_data = self.settings_page.get_user_data_by_user_name(ui_consts.READ_ONLY_USERNAME)
        assert self.settings_page.VIEWER_ROLE in user_data

        # Change to Read Only role, save the user and check permissions correct also after refresh
        self.settings_page.click_edit_user(ui_consts.READ_ONLY_USERNAME)
        self.settings_page.wait_for_new_user_panel()
        self.settings_page.select_role(self.settings_page.RESTRICTED_ROLE)
        self.settings_page.save_user_wait_done()
        user_data = self.settings_page.get_user_data_by_user_name(ui_consts.READ_ONLY_USERNAME)
        assert self.settings_page.RESTRICTED_ROLE in user_data
        self.settings_page.refresh()
        self.settings_page.click_manage_users_settings()
        user_data = self.settings_page.get_user_data_by_user_name(ui_consts.READ_ONLY_USERNAME)
        assert self.settings_page.RESTRICTED_ROLE in user_data

    def _enter_user_management_and_create_restricted_user(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        self.settings_page.create_new_user(ui_consts.RESTRICTED_USERNAME,
                                           ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME,
                                           ui_consts.LAST_NAME,
                                           self.settings_page.RESTRICTED_ROLE)
        self.settings_page.wait_for_user_created_toaster()

    def test_user_predefined_role_duplicate_and_change(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                         ui_consts.NEW_PASSWORD,
                                                         ui_consts.FIRST_NAME,
                                                         ui_consts.LAST_NAME,
                                                         self.settings_page.RESTRICTED_ROLE)

        user = self.settings_page.get_user_object_by_user_name(ui_consts.RESTRICTED_USERNAME)

        self.settings_page.click_manage_roles_settings()

        assert user.role != self.settings_page.RESTRICTED_ROLE

        self.settings_page.click_role_by_name(user.role)
        self.settings_page.wait_for_side_panel()
        self.settings_page.get_role_edit_panel_action().click()

        self.settings_page.select_permissions({
            'devices_assets': [
                'View devices',
            ]
        })
        self.settings_page.click_save_button()
        self.settings_page.safeguard_click_confirm('Yes')
        self.settings_page.wait_for_role_successfully_saved_toaster()

    def test_change_role_while_user_is_logged_in(self):
        role_name = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)

        self.login_page.switch_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        new_test_user_roles = self.open_another_session(incognito_mode=True)
        new_test_user_roles.login_page.login(self.username, self.password)
        self.base_page.wait_for_run_research()

        new_permissions = {
            'settings': 'all'
        }
        # Check changing of the another session logged in user's role
        new_test_user_roles.settings_page.update_role(role_name, new_permissions, True)
        new_test_user_roles.quit_browser()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.base_page.wait_for_run_research()
        self.login_page.assert_logged_in()
        new_permissions = {
            'reports': 'all'
        }
        # Check changing of the current logged in user's role
        self.settings_page.update_role(role_name, new_permissions, True)
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.base_page.wait_for_run_research()
        self.login_page.assert_logged_in()
