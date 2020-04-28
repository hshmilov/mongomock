import pytest

from ui_tests.pages.reports_page import ReportConfig
from ui_tests.tests import ui_consts
from ui_tests.tests.ui_test_base import TestBase


# pylint: disable=no-member


class TestReportsPermissions(TestBase):
    DATA_QUERY = 'specific_data.data.name == regex(\' no\', \'i\')'

    TEST_REPORT_READ_ONLY_QUERY = 'query for read only test'
    TEST_REPORT_READ_ONLY_NAME = 'report name read only'
    TEST_REPORT_CAN_ADD_NAME = 'report name can add'
    TEST_REPORT_CAN_EDIT_NAME = 'report name can EDIT'

    TEST_USERS_QUERY = 'query for users'

    def test_report_permissions(self):
        self.reports_page.switch_to_page()
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.fill_filter(self.DATA_QUERY)
        self.devices_page.enter_search()
        self.devices_page.click_save_query()
        self.devices_page.fill_query_name(self.TEST_REPORT_READ_ONLY_QUERY)
        self.devices_page.click_save_query_save_button()
        self.devices_page.wait_for_table_to_load()
        device_queries = [{'entity': 'Devices', 'name': self.TEST_REPORT_READ_ONLY_QUERY}]

        self.reports_page.switch_to_page()
        self.reports_page.create_report(ReportConfig(report_name=self.TEST_REPORT_READ_ONLY_NAME,
                                                     add_dashboard=True, queries=device_queries))
        self.reports_page.wait_for_table_to_load()
        settings_permissions = {
            'reports': [
                'View reports'
            ]
        }
        self._test_reports_with_only_view_permission(settings_permissions, user_role)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'reports',
                                                     'Add report',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self._test_reports_with_add_permission(device_queries)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'reports',
                                                     'Edit reports',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self._test_reports_with_edit_permissions()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'reports',
                                                     'Delete report',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_reports_with_delete_permission()

    def test_reports_entities_permissions(self):
        self.reports_page.switch_to_page()
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.fill_filter(self.DATA_QUERY)
        self.devices_page.enter_search()
        self.devices_page.click_save_query()
        self.devices_page.fill_query_name(self.TEST_REPORT_READ_ONLY_QUERY)
        self.devices_page.click_save_query_save_button()
        self.devices_page.wait_for_table_to_load()
        device_queries = [{'entity': 'Devices', 'name': self.TEST_REPORT_READ_ONLY_QUERY}]

        self.users_page.switch_to_page()
        self.users_page.wait_for_table_to_load()
        self.users_page.fill_filter(self.DATA_QUERY)
        self.users_page.enter_search()
        self.users_page.click_save_query()
        self.users_page.fill_query_name(self.TEST_USERS_QUERY)
        self.users_page.click_save_query_save_button()
        self.users_page.wait_for_table_to_load()
        users_queries = [{'entity': 'Users', 'name': self.TEST_USERS_QUERY}]

        self.reports_page.switch_to_page()
        self.reports_page.create_report(ReportConfig(report_name=self.TEST_REPORT_READ_ONLY_NAME,
                                                     add_dashboard=True, queries=device_queries))
        self.reports_page.wait_for_table_to_load()
        settings_permissions = {
            'reports': [
                'View reports',
                'Add report'
            ],
        }

        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.logout_and_login_with_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        self.reports_page.click_new_report()
        self.reports_page.click_include_queries()
        self.reports_page.assert_select_saved_views_is_empty(0)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'devices_assets',
                                                     'View devices',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self.reports_page.switch_to_page()
        self.reports_page.click_new_report()
        self.reports_page.click_include_queries()
        for index, query in enumerate(device_queries):
            self.reports_page.select_saved_view_from_multiple(index, query['name'], query['entity'])
            if index < len(device_queries) - 1:
                self.reports_page.click_add_query()
            self.reports_page.click_add_query()
        assert self.reports_page.select_saved_view(self.TEST_USERS_QUERY, 'Users') is None

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'users_assets',
                                                     'View users',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self.reports_page.switch_to_page()
        self.reports_page.click_new_report()
        self.reports_page.click_include_queries()
        self.reports_page.select_saved_views(device_queries)
        self.reports_page.click_add_query()
        self.reports_page.select_saved_views(users_queries)

    def _test_reports_with_delete_permission(self):
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        assert not self.reports_page.is_disabled_new_report_button()
        assert not self.reports_page.is_row_checkbox_absent()
        self.reports_page.click_row_checkbox()
        self.reports_page.click_remove_reports(True)

    def _test_reports_with_edit_permissions(self):
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        assert not self.reports_page.is_disabled_new_report_button()
        assert self.reports_page.is_row_checkbox_absent()
        self.reports_page.click_report(self.TEST_REPORT_CAN_ADD_NAME)
        assert not self.reports_page.is_form_disabled()
        assert not self.reports_page.is_save_button_disabled()
        self.reports_page.click_save()

    def _test_reports_with_add_permission(self, queries):
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        assert not self.reports_page.is_disabled_new_report_button()
        assert self.reports_page.is_row_checkbox_absent()
        with pytest.raises(AssertionError, match='Could not find option Devices'):
            self.reports_page.create_report(ReportConfig(report_name=self.TEST_REPORT_CAN_ADD_NAME,
                                                         add_dashboard=True, queries=queries))
        self.reports_page.close_dropdown()
        self.reports_page.switch_to_page()
        self.reports_page.create_report(ReportConfig(report_name=self.TEST_REPORT_CAN_ADD_NAME,
                                                     add_dashboard=True, queries=None))
        self.reports_page.click_report(self.TEST_REPORT_CAN_ADD_NAME)
        assert self.reports_page.is_form_disabled()
        assert self.reports_page.is_save_button_disabled()

    def _test_reports_with_only_view_permission(self, settings_permissions, user_role):
        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.logout_and_login_with_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        assert self.reports_page.is_disabled_new_report_button()
        assert self.reports_page.is_row_checkbox_absent()
        self.reports_page.click_report(self.TEST_REPORT_READ_ONLY_NAME)
        assert self.reports_page.is_form_disabled()
        assert self.reports_page.is_save_button_disabled()
