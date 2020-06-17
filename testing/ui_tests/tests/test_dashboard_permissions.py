import pytest
from selenium.common.exceptions import NoSuchElementException

from axonius.consts.gui_consts import DASHBOARD_SPACE_PERSONAL
from axonius.utils.wait import wait_until
from ui_tests.pages.reports_page import ReportConfig
from ui_tests.tests import ui_consts
from ui_tests.tests.permissions_test_base import PermissionsTestBase


# pylint: disable=no-member


class TestDashboardPermissions(PermissionsTestBase):
    TEST_EMPTY_TITLE = 'test empty'
    TEST_MOVE_TITLE = 'test move'
    OSX_OPERATING_SYSTEM_NAME = 'OS X Operating System'
    OSX_OPERATING_SYSTEM_FILTER = 'specific_data.data.os.type == "OS X"'

    TEST_SPACE_NAME = 'test space'
    TEST_SPACE_NAME_RENAME = 'test rename'
    TEST_RENAME_SPACE_NAME = 'rename space'
    TEST_REPORT_NAME = 'testonius'
    NOTE_TEXT = 'note text'

    def test_dashboard_permissions(self):
        self.settings_page.disable_getting_started_feature()
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        self.devices_page.create_saved_query(self.OSX_OPERATING_SYSTEM_FILTER, self.OSX_OPERATING_SYSTEM_NAME)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_segmentation_card(module='Devices',
                                                  field=ui_consts.OS_TYPE_OPTION_NAME,
                                                  title=self.TEST_MOVE_TITLE,
                                                  view_name=self.OSX_OPERATING_SYSTEM_NAME)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_new_space(self.TEST_RENAME_SPACE_NAME)

        self.login_page.switch_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD, None, False)

        settings_permissions = {
            'dashboard': [],
            'devices_assets': [
                'Run saved queries',
                'Create saved query',
            ]
        }

        self.dashboard_page.switch_to_page()
        assert self.dashboard_page.is_missing_space(DASHBOARD_SPACE_PERSONAL)
        assert self.dashboard_page.is_new_chart_card_missing()
        with pytest.raises(NoSuchElementException):
            self.dashboard_page.find_search_insights()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'devices_assets',
                                                     'View devices',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD,
                                                     False)
        self.dashboard_page.switch_to_page()
        assert self.dashboard_page.find_search_insights()
        self.dashboard_page.fill_query_value('cb')
        self.dashboard_page.enter_search()
        self.dashboard_page.wait_for_table_to_load()
        assert len(self.dashboard_page.get_search_insights_tables()) == 1
        self.dashboard_page.assert_device_explorer_results_exists()

        self._test_chart_permissions(settings_permissions, user_role)
        self._test_spaces_permissions(settings_permissions, user_role)
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'users_assets',
                                                     'View users',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD,
                                                     False)
        self.dashboard_page.switch_to_page()
        assert self.dashboard_page.find_search_insights()
        self.dashboard_page.fill_query_value('cb')
        self.dashboard_page.enter_search()
        self.dashboard_page.wait_for_table_to_load()
        assert len(self.dashboard_page.get_search_insights_tables()) == 2
        self.dashboard_page.assert_device_explorer_results_exists()
        self.dashboard_page.assert_users_explorer_results_exists()

    def _test_chart_permissions(self, settings_permissions, user_role):
        self.dashboard_page.switch_to_page()
        assert not self.dashboard_page.is_remove_card_button_present(self.TEST_MOVE_TITLE)
        assert not self.dashboard_page.is_edit_card_button_present(self.TEST_MOVE_TITLE)
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'dashboard',
                                                     'Edit charts',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD,
                                                     False)
        self.dashboard_page.switch_to_page()
        assert not self.dashboard_page.is_remove_card_button_present(self.TEST_MOVE_TITLE)
        assert self.dashboard_page.is_edit_card_button_present(self.TEST_MOVE_TITLE)
        self.dashboard_page.edit_card(self.TEST_MOVE_TITLE)
        self.dashboard_page.click_card_save()
        self.dashboard_page.open_move_or_copy_card(self.TEST_MOVE_TITLE)
        assert self.dashboard_page.is_move_or_copy_checkbox_disabled()
        self.dashboard_page.close_move_or_copy_dialog()

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'dashboard',
                                                     'Add chart',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD,
                                                     False)
        self.dashboard_page.switch_to_page()
        assert not self.dashboard_page.is_missing_space(DASHBOARD_SPACE_PERSONAL)
        self.dashboard_page.click_tab(DASHBOARD_SPACE_PERSONAL)
        assert not self.dashboard_page.is_new_chart_card_missing()
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_segmentation_card(module='Devices',
                                                  field=ui_consts.OS_TYPE_OPTION_NAME,
                                                  title=self.TEST_EMPTY_TITLE,
                                                  view_name=self.OSX_OPERATING_SYSTEM_NAME)
        assert not self.dashboard_page.is_remove_card_button_present(self.TEST_EMPTY_TITLE)
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'dashboard',
                                                     'Delete chart',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD,
                                                     False)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.click_tab(DASHBOARD_SPACE_PERSONAL)
        assert self.dashboard_page.is_remove_card_button_present(self.TEST_EMPTY_TITLE)
        assert self.dashboard_page.is_edit_card_button_present(self.TEST_EMPTY_TITLE)
        self.dashboard_page.remove_card(self.TEST_EMPTY_TITLE)

    def _test_spaces_permissions(self, settings_permissions, user_role):
        assert self.dashboard_page.is_missing_add_space()
        self.dashboard_page.assert_disabled_space_menu(3)
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'dashboard',
                                                     'Add and Edit Spaces',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD,
                                                     False)
        self.dashboard_page.switch_to_page()
        assert not self.dashboard_page.is_missing_add_space()
        self.dashboard_page.add_new_space(self.TEST_SPACE_NAME)
        wait_until(lambda: self.dashboard_page.find_space_header_title(4) == self.TEST_SPACE_NAME)
        assert self.dashboard_page.is_missing_remove_space(4)
        self.dashboard_page.edit_space(self.TEST_SPACE_NAME_RENAME, index=4)
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'dashboard',
                                                     'Delete space',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD,
                                                     False)
        self.dashboard_page.switch_to_page()
        assert not self.dashboard_page.is_missing_add_space()
        assert not self.dashboard_page.is_missing_remove_space()
        self.dashboard_page.remove_space()
        self.dashboard_page.remove_space()

    def _assert_space_for_user(self, user_name, user_password, missing_space_name, exist_space_name):
        self.login_page.switch_user(user_name, user_password)
        # wait for the first spaces fetch to complete
        self.dashboard_page.wait_for_spinner_to_end()
        assert self.dashboard_page.is_missing_space(missing_space_name)
        assert not self.dashboard_page.is_missing_space(exist_space_name)

    def test_dashboard_space_roles(self):
        self.base_page.run_discovery()
        users = []
        user_roles = []
        for i in range(2):
            index_string = str(i)
            users.append(ui_consts.VIEWER_USERNAME + index_string)
            user_roles.append(self.settings_page.add_user_with_duplicated_role(users[i],
                                                                               ui_consts.NEW_PASSWORD,
                                                                               ui_consts.FIRST_NAME,
                                                                               ui_consts.LAST_NAME,
                                                                               self.settings_page.VIEWER_ROLE))
            self.dashboard_page.switch_to_page()
            self.dashboard_page.add_new_space(self.TEST_SPACE_NAME + index_string,
                                              [self.settings_page.VIEWER_ROLE, user_roles[i]])

        for i in range(2):
            missing_space_name = self.TEST_SPACE_NAME + str(abs(i - 1))
            exist_space_name = self.TEST_SPACE_NAME + str(i)
            self._assert_space_for_user(users[i],
                                        ui_consts.NEW_PASSWORD,
                                        missing_space_name,
                                        exist_space_name)

        self.login_page.logout_and_login_with_admin()
        # wait for the first spaces fetch to complete
        self.dashboard_page.wait_for_spinner_to_end()
        for i in range(2):
            assert not self.dashboard_page.is_missing_space(self.TEST_SPACE_NAME + str(i))

    def test_edit_report_with_restricted_space(self):
        self.base_page.run_discovery()
        self.settings_page.add_user_with_duplicated_role(ui_consts.VIEWER_USERNAME,
                                                         ui_consts.NEW_PASSWORD,
                                                         ui_consts.FIRST_NAME,
                                                         ui_consts.LAST_NAME,
                                                         self.settings_page.VIEWER_ROLE)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_new_space(self.TEST_SPACE_NAME, [self.settings_page.VIEWER_ROLE])
        self.reports_page.switch_to_page()
        self.reports_page.create_report(ReportConfig(report_name=self.TEST_REPORT_NAME, add_dashboard=True,
                                                     spaces=[self.TEST_SPACE_NAME]))
        self.reports_page.wait_for_table_to_load()
        self.reports_page.click_report(self.TEST_REPORT_NAME)
        self.reports_page.wait_for_spinner_to_end()
        assert not self.reports_page.is_dashboard_checkbox_disabled()
        self.login_page.switch_user(ui_consts.VIEWER_USERNAME, ui_consts.NEW_PASSWORD)
        self.dashboard_page.wait_for_spinner_to_end()
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        self.reports_page.click_report(self.TEST_REPORT_NAME)
        self.reports_page.wait_for_spinner_to_end()
        assert self.reports_page.is_restricted_report_modal_exist()
        self.reports_page.click_restricted_report_modal_confirm()
        self.reports_page.wait_for_table_to_be_responsive()
        self.login_page.logout_and_login_with_admin()
