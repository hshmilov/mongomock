import pytest
from selenium.common.exceptions import (TimeoutException as SeleniumTimeoutException,
                                        NoSuchElementException)
from axonius.consts.gui_consts import DASHBOARD_SPACE_PERSONAL
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import (NEW_PASSWORD, VIEWER_USERNAME, VIEWER_ADDER_USERNAME, FIRST_NAME, LAST_NAME)
from test_credentials.test_gui_credentials import DEFAULT_USER


class TestPrivateQuery(TestBase):
    INITIAL_QUERY_NAME = 'Initial query name'
    PUBLIC_QUERY_SAVE_NAME = 'This is a public query by {user_name}'
    PRIVATE_QUERY_SAVE_NAME = 'This is a private query by {user_name}'
    CHART_NAME = 'Comparison chart'

    def test_private_query(self):
        """
        Testing private query operations, including filtering and making sure it appears only
        on relevant pages with a series of checks:
        1 - Check private query operations for user with "admin" role.
        2 - Check private query operations for user with "viewer" role.
        3 - Check private query operations for user with "view_and_add" role. ( User can also add query )
        4 - Check that private query doesn't appear in: Reports, EC Config, Query Wizard, and also
            doesn't appear in any chart wizard opened from dashboard spaces besides "My Dashboard"
        5 - Check that private query appears in: Devices query search input (inside the dropdown)
            And also appears in chart wizard at "My Dashboard"
        6 - Check that if a dashboard chart contains a private query, it cannot be moved/copied
            to any space besides "My Dashboard"
        """

        self.settings_page.switch_to_page()
        self.base_page.run_discovery()

        # Check 1:
        self._test_admin_private_query()

        # Check 2:
        private_viewer_query_name = self.PRIVATE_QUERY_SAVE_NAME.format(user_name='Viewer')
        self._test_viewer_private_query(private_viewer_query_name)

        # Check 3:
        public_viewer_adder_query_name = self.PUBLIC_QUERY_SAVE_NAME.format(user_name='Viewer Adder')
        private_viewer_adder_query_name = self.PRIVATE_QUERY_SAVE_NAME.format(user_name='Viewer Adder')
        self._test_viewer_adder_private_query(public_viewer_adder_query_name, private_viewer_adder_query_name)

        # Check 4:
        self._test_private_query_not_appearing()

        # Check 5:
        self._test_private_query_appearing(private_viewer_adder_query_name)

        # Check 6:
        self._test_chart_with_private_query()

    def _test_admin_private_query(self):
        public_admin_query = self.PUBLIC_QUERY_SAVE_NAME.format(user_name='Admin')
        self.devices_page.create_private_query(self.INITIAL_QUERY_NAME)
        self.devices_page.assert_private_query_checkbox_hidden(self.INITIAL_QUERY_NAME)
        self.devices_page.rename_query(self.INITIAL_QUERY_NAME, public_admin_query)
        self._assert_private_query_created_and_renamed(public_admin_query)
        self._assert_private_query_set_public(public_admin_query)

    def _test_viewer_private_query(self, private_viewer_query_name):
        self._create_and_login_user(VIEWER_USERNAME, self.settings_page.VIEWER_PERMISSIONS)
        self.devices_page.create_private_query(self.INITIAL_QUERY_NAME)
        self.devices_page.rename_query(self.INITIAL_QUERY_NAME, private_viewer_query_name)
        self._assert_private_query_created_and_renamed(private_viewer_query_name)
        self.devices_queries_page.click_query_row_by_name(private_viewer_query_name)
        with pytest.raises(SeleniumTimeoutException):
            self.devices_queries_page.get_set_public_panel_action()
        assert self.devices_queries_page.get_edit_panel_action()
        self.devices_queries_page.get_remove_panel_action().click()
        self.devices_queries_page.safeguard_click_confirm(self.devices_queries_page.SAFEGUARD_REMOVE_BUTTON_SINGLE)
        self.devices_queries_page.wait_for_table_to_be_responsive()
        name_cell_index = self.devices_queries_page.count_sort_column(self.devices_queries_page.NAME_COLUMN)
        name = self.devices_queries_page.get_row_cell_text(1, name_cell_index)
        assert name != private_viewer_query_name
        self.devices_page.create_private_query(private_viewer_query_name)

    def _test_viewer_adder_private_query(self, public_viewer_adder_query_name, private_viewer_adder_query_name):
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=DEFAULT_USER['user_name'], password=DEFAULT_USER['password'])
        self._create_and_login_user(VIEWER_ADDER_USERNAME, self.settings_page.VIEWER_ADDER_PERMISSIONS)
        self.devices_page.create_private_query(public_viewer_adder_query_name)
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_be_responsive()
        self._assert_private_query_set_public(public_viewer_adder_query_name)
        self.devices_page.create_private_query(private_viewer_adder_query_name)

    def _test_private_query_not_appearing(self):
        self.reports_page.get_to_new_report_page()
        self.reports_page.click_include_queries()
        self.devices_queries_page.assert_private_query_not_selectable(
            self.PRIVATE_QUERY_SAVE_NAME.format(user_name=''),
            self.devices_queries_page.SELECT_QUERY_NAME_CSS)
        self.enforcements_page.switch_to_page()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.select_trigger()
        self.devices_queries_page.assert_private_query_not_selectable(
            self.PRIVATE_QUERY_SAVE_NAME.format(user_name=''),
            self.devices_queries_page.SELECT_QUERY_NAME_CSS)
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        self.devices_page.select_query_field(self.devices_page.FIELD_SAVED_QUERY)
        with pytest.raises(NoSuchElementException):
            self.devices_page.select_query_value(self.PRIVATE_QUERY_SAVE_NAME.format(user_name=''))
        self.devices_page.key_down_escape()  # so that search button will be clickable
        self.devices_page.click_search()
        self.devices_page.wait_for_table_to_be_responsive()
        self.dashboard_page.switch_to_page()
        self.dashboard_page.open_new_card_wizard()
        self.dashboard_page.select_chart_metric('Query Comparison')
        self.devices_queries_page.assert_private_query_not_selectable(
            self.PRIVATE_QUERY_SAVE_NAME.format(user_name=''),
            self.devices_queries_page.SELECT_VIEW_NAME_CSS)
        self.dashboard_page.feedback_modal_click_cancel()

    def _test_private_query_appearing(self, private_viewer_adder_query_name):
        self.devices_page.switch_to_page()
        self.devices_page.check_search_list_for_names([private_viewer_adder_query_name])
        self.dashboard_page.switch_to_page()
        self.dashboard_page.find_space_header(2).click()
        self.dashboard_page.add_comparison_card([{'module': 'Devices', 'query': private_viewer_adder_query_name},
                                                 {'module': 'Devices', 'query': private_viewer_adder_query_name}],
                                                self.CHART_NAME)

    def _test_chart_with_private_query(self):
        self.dashboard_page.open_move_or_copy_card(self.CHART_NAME)
        spaces = self.dashboard_page.get_all_spaces_for_move_or_copy()
        assert (len(spaces) == 1 and spaces[0] == DASHBOARD_SPACE_PERSONAL)

    def _assert_private_query_created_and_renamed(self, query_name):
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_be_responsive()
        access_cell_index = self.devices_queries_page.count_sort_column(self.devices_queries_page.ACCESS_COLUMN)
        access = self.devices_queries_page.get_row_cell_text(1, access_cell_index)
        assert access == 'Private'
        name_cell_index = self.devices_queries_page.count_sort_column(self.devices_queries_page.NAME_COLUMN)
        name = self.devices_queries_page.get_row_cell_text(1, name_cell_index)
        assert name == query_name

    def _assert_private_query_set_public(self, query_name):
        self.devices_queries_page.click_query_row_by_name(query_name)
        with pytest.raises(SeleniumTimeoutException):
            self.devices_queries_page.get_enforce_panel_action()
        self.devices_queries_page.set_query_public()
        access_cell_index = self.devices_queries_page.count_sort_column(self.devices_queries_page.ACCESS_COLUMN)
        access = self.devices_queries_page.get_row_cell_text(1, access_cell_index)
        assert access == 'Public'
        self.devices_page.switch_to_page()
        self.devices_page.reset_query()

    def _create_and_login_user(self, user_name, permissions):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user_with_new_permission(user_name,
                                                               NEW_PASSWORD,
                                                               FIRST_NAME,
                                                               LAST_NAME,
                                                               permissions)
        self.settings_page.wait_for_user_created_toaster()
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=user_name, password=NEW_PASSWORD)
