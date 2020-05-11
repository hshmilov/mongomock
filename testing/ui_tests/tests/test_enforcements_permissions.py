import pytest
from selenium.common.exceptions import NoSuchElementException

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
        self.enforcements_page.create_basic_enforcement(enforcement_name, MANAGED_DEVICES_QUERY_NAME)
        recipient = generate_random_valid_email()
        self.enforcements_page.add_main_action_send_email(enforcement_action_name, recipient=recipient)

        self.enforcements_page.wait_for_table_to_load()
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
        self._test_enforcements_with_add_permission()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'enforcements',
                                                     'Delete Enforcement',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self._test_enforcements_with_delete_permission()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'enforcements',
                                                     'Edit Enforcement',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self._test_enforcements_with_edit_permission()

    def _test_enforcements_with_only_view_permission(self, settings_permissions, user_role, enforcement_name):
        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.switch_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.is_view_tasks_button_disabled()
        assert self.enforcements_page.is_disabled_new_enforcement_button()
        assert self.enforcements_page.is_row_checkbox_absent()
        self.enforcements_page.click_enforcement(enforcement_name)
        with pytest.raises(NoSuchElementException):
            self.enforcements_page.get_save_button()

    def _test_enforcements_with_add_permission(self):
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        assert not self.enforcements_page.is_disabled_new_enforcement_button()
        assert self.reports_page.is_row_checkbox_absent()
        new_enforcement_name = 'only add enforcement'
        new_enforcement_action_name = 'only add enforcement action'
        self.enforcements_page.create_basic_enforcement(new_enforcement_name, MANAGED_DEVICES_QUERY_NAME)
        recipient = generate_random_valid_email()
        self.enforcements_page.add_main_action_send_email(new_enforcement_action_name, recipient=recipient)

        self.enforcements_page.click_enforcement(new_enforcement_name)
        with pytest.raises(NoSuchElementException):
            self.enforcements_page.get_save_button()

    def _test_enforcements_with_delete_permission(self):
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        assert not self.enforcements_page.is_disabled_new_enforcement_button()
        assert not self.reports_page.is_row_checkbox_absent()
        new_enforcement_name = 'with delete enforcement'
        new_enforcement_action_name = 'with delete enforcement action'
        self.enforcements_page.create_basic_enforcement(new_enforcement_name, MANAGED_DEVICES_QUERY_NAME)
        recipient = generate_random_valid_email()
        self.enforcements_page.add_main_action_send_email(new_enforcement_action_name, recipient=recipient)

        self.enforcements_page.click_enforcement(new_enforcement_name)
        with pytest.raises(NoSuchElementException):
            self.enforcements_page.get_save_button()

        self.enforcements_page.click_exit_button()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_select_enforcement(1)
        self.enforcements_page.remove_selected_enforcements(True)

    def _test_enforcements_with_edit_permission(self):
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        assert not self.enforcements_page.is_disabled_new_enforcement_button()
        assert not self.reports_page.is_row_checkbox_absent()
        new_enforcement_name = 'with edit enforcement'
        new_enforcement_action_name = 'with edit enforcement action'
        self.enforcements_page.create_basic_enforcement(new_enforcement_name, MANAGED_DEVICES_QUERY_NAME)
        recipient = generate_random_valid_email()
        self.enforcements_page.add_main_action_send_email(new_enforcement_action_name, recipient=recipient)

        self.enforcements_page.click_enforcement(new_enforcement_name)
        self.enforcements_page.click_save_button()

        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_select_enforcement(2)
        self.enforcements_page.remove_selected_enforcements(True)
