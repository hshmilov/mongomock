from services.standalone_services.smtp_service import generate_random_valid_email
from ui_tests.tests import ui_consts
from ui_tests.tests.ui_consts import MANAGED_DEVICES_QUERY_NAME, EmailSettings
from ui_tests.tests.permissions_test_base import PermissionsTestBase


# pylint: disable=no-member


class TestEnforcementsPermissions(PermissionsTestBase):

    def test_enforcements_permissions(self):
        self.settings_page.switch_to_page()
        self.settings_page.add_email_server(EmailSettings.host, EmailSettings.port)

        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)

        self.enforcements_page.switch_to_page()
        enforcement_name = 'test_empty_enforcement'
        enforcement_action_name = 'test_email_action'
        self._create_send_email_enforcement_and_trigger(enforcement_name, enforcement_action_name)

        settings_permissions = {
            'enforcements': [
                'View Enforcement Center'
            ],
            'devices_assets': [
                'View devices'
            ]
        }
        self._test_enforcements_with_only_view_permission(settings_permissions, user_role, enforcement_name)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'enforcements',
                                                     'View Enforcement Tasks',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.enforcements_page.switch_to_page()
        assert not self.enforcements_page.is_view_tasks_button_disabled()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'enforcements',
                                                     'Add Enforcement',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self._test_enforcements_with_add_permission(enforcement_name)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'enforcements',
                                                     'Delete Enforcement',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self._test_enforcements_with_delete_permission(enforcement_name)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'enforcements',
                                                     'Edit Enforcement',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self._test_enforcements_with_edit_permission()

    def test_enforcements_deploy_action_permission(self):
        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)

        settings_permissions = {
            'enforcements': [
                'View Enforcement Center',
                'Add Enforcement',
                'Edit Enforcement'
            ],
            'devices_assets': [
                'View devices'
            ]
        }
        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.switch_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.enforcements_page.create_basic_empty_enforcement(self.enforcements_page.RUN_CMD_ENFORCEMENT_NAME)
        self.enforcements_page.add_run_windows_command('test deploy')
        self.login_page.assert_logged_in()

    def _test_enforcements_with_only_view_permission(self, settings_permissions, user_role, enforcement_name):
        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.switch_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_be_responsive()
        assert self.enforcements_page.is_view_tasks_button_disabled()
        assert self.enforcements_page.is_disabled_new_enforcement_button()
        assert self.enforcements_page.is_row_checkbox_absent()
        self.enforcements_page.click_enforcement(enforcement_name)
        self.enforcements_page.assert_config_panel_in_display_mode()
        assert self.enforcements_page.is_view_tasks_button_disabled()
        assert self.enforcements_page.is_run_button_disabled()

    def _test_enforcements_with_add_permission(self, enforcement_name):
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_be_responsive()
        assert self.enforcements_page.is_row_checkbox_absent()
        assert self.enforcements_page.is_disabled_new_enforcement_button()
        self.enforcements_page.click_enforcement(enforcement_name)
        self.enforcements_page.assert_config_panel_in_edit_mode()

    def _test_enforcements_with_delete_permission(self, enforcement_name):
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_be_responsive()
        assert not self.enforcements_page.is_row_checkbox_absent()
        assert self.enforcements_page.is_disabled_new_enforcement_button()
        self.enforcements_page.click_enforcement(enforcement_name)
        self.enforcements_page.assert_config_panel_in_edit_mode()

    def _test_enforcements_with_edit_permission(self):
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_be_responsive()
        assert not self.enforcements_page.is_disabled_new_enforcement_button()
        assert not self.enforcements_page.is_row_checkbox_absent()
        new_enforcement_name = 'with edit enforcement'
        new_enforcement_action_name = 'with edit enforcement action'
        self._create_send_email_enforcement_and_trigger(new_enforcement_name, new_enforcement_action_name)
        self.enforcements_page.click_enforcement(new_enforcement_name)
        assert self.enforcements_page.edit_button_exists()
        assert self.enforcements_page.delete_button_exists()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_be_responsive()
        self.enforcements_page.click_select_enforcement(2)
        self.enforcements_page.remove_selected_enforcements(True)

    def _create_send_email_enforcement_and_trigger(self, enforcement_name, main_action_name):
        self.enforcements_page.create_basic_enforcement(enforcement_name)
        recipient = generate_random_valid_email()
        self.enforcements_page.add_main_action_send_email(main_action_name, recipient=recipient)
        self.enforcements_page.create_trigger(MANAGED_DEVICES_QUERY_NAME)
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_be_responsive()
