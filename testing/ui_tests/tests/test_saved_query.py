from datetime import datetime
import copy
from uuid import uuid4
import pytest
from selenium.common.exceptions import TimeoutException as SeleniumTimeoutException
from axonius.utils.wait import wait_until
from axonius.utils.parsing import normalize_timezone_date
from axonius.consts.gui_consts import PREDEFINED_PLACEHOLDER
from services.plugins.device_control_service import DeviceControlService
from services.axon_service import TimeoutException
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import (READ_ONLY_USERNAME, NEW_PASSWORD,
                                      UPDATE_USERNAME, UPDATE_PASSWORD, UPDATE_FIRST_NAME, UPDATE_LAST_NAME,
                                      WINDOWS_QUERY_NAME, LINUX_QUERY_NAME, JSON_ADAPTER_NAME,
                                      VIEWER_USERNAME, VIEWER_ADDER_USERNAME, FIRST_NAME, LAST_NAME)
from test_credentials.json_file_credentials import (DEVICE_FIRST_HOSTNAME, DEVICE_SECOND_NAME)
from test_credentials.test_gui_credentials import DEFAULT_USER


class TestSavedQuery(TestBase):
    NEW_QUERY_TITLE = 'New Query'
    UNSAVED_QUERY_STATUS = '[Unsaved]'
    EDITED_QUERY_STATUS = '[Edited]'
    CUSTOM_QUERY_SAVE_NAME_1 = 'A Saved Query'
    CUSTOM_QUERY_SAVE_NAME_2 = 'Another Saved Query'
    CUSTOM_QUERY_SAVE_NAME_3 = 'Alternate Saved Query'
    ENFORCEMENT_NAME = 'An Enforcement'

    ADMIN_NAME = 'administrator'

    ADMIN_DISPLAY_NAME = 'internal/admin'

    JSON_ASSET_ENTITY_QUERY_NAME = 'JSON Asset Entity Query'

    INITIAL_QUERY_NAME = 'Initial query name'
    PUBLIC_QUERY_SAVE_NAME = 'This is a public query by {user_name}'
    PRIVATE_QUERY_SAVE_NAME = 'This is a private query by {user_name}'

    @pytest.mark.skip('ad change')
    def test_query_state(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_query_title_text() == self.NEW_QUERY_TITLE
        assert self.devices_page.find_query_status_text() == self.UNSAVED_QUERY_STATUS
        assert self.devices_page.is_query_save_as_disabled()

        # Save is enabled when user changes: Filter \ Columns \ Sort \ Column Filters
        self.devices_page.build_query_active_directory()
        assert not self.devices_page.is_query_save_as_disabled()
        # Remove host name field
        self.devices_page.edit_columns(remove_col_names=[self.devices_page.FIELD_TAGS])
        assert not self.devices_page.is_query_save_as_disabled()
        self.devices_page.fill_enter_table_search('')
        assert not self.devices_page.is_query_save_as_disabled()
        # Add host name field
        self.devices_page.edit_columns(add_col_names=[self.devices_page.FIELD_TAGS])
        assert self.devices_page.is_query_save_as_disabled()
        # Sort host name field
        self.devices_page.click_sort_column(self.devices_page.FIELD_HOSTNAME_TITLE)
        assert not self.devices_page.is_query_save_as_disabled()
        # No sort host name field
        self.devices_page.click_sort_column(self.devices_page.FIELD_HOSTNAME_TITLE)
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.click_sort_column(self.devices_page.FIELD_HOSTNAME_TITLE)
        assert self.devices_page.is_query_save_as_disabled()
        # Filter host name field
        self.devices_page.filter_column(self.devices_page.FIELD_HOSTNAME_TITLE, [{'term': 'test'}])
        assert not self.devices_page.is_query_save_as_disabled()
        # No filter host name field
        self.devices_page.filter_column(self.devices_page.FIELD_HOSTNAME_TITLE, [{'term': ''}])
        assert self.devices_page.is_query_save_as_disabled()
        self.devices_page.build_query_active_directory()

        # Save query from current view
        self.devices_page.save_query(self.CUSTOM_QUERY_SAVE_NAME_1)
        assert self.devices_page.find_query_title_text() == self.CUSTOM_QUERY_SAVE_NAME_1
        # Save query from currently presented query
        self.devices_page.save_query_as(self.CUSTOM_QUERY_SAVE_NAME_2)
        assert self.devices_page.find_query_title_text() == self.CUSTOM_QUERY_SAVE_NAME_2
        self.devices_page.check_search_list_for_names([self.CUSTOM_QUERY_SAVE_NAME_1, self.CUSTOM_QUERY_SAVE_NAME_2])
        # Rename currently presented query
        self.devices_page.rename_query(self.CUSTOM_QUERY_SAVE_NAME_2, self.CUSTOM_QUERY_SAVE_NAME_3)
        assert self.devices_page.find_query_title_text() == self.CUSTOM_QUERY_SAVE_NAME_3
        self.devices_page.check_search_list_for_names([self.CUSTOM_QUERY_SAVE_NAME_1, self.CUSTOM_QUERY_SAVE_NAME_3])
        assert self.devices_page.find_query_status_text() == ''

    @pytest.mark.skip('ad change')
    def test_edit_saved_query(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_query_title_text() == self.NEW_QUERY_TITLE
        assert self.devices_page.find_query_status_text() == self.UNSAVED_QUERY_STATUS
        self.devices_page.build_query_active_directory()
        self.devices_page.save_query(self.CUSTOM_QUERY_SAVE_NAME_1)
        self.devices_page.reset_query()
        self.devices_page.execute_saved_query(self.CUSTOM_QUERY_SAVE_NAME_1)
        assert self.devices_page.find_query_status_text() == ''
        self.devices_page.add_query_last_seen_last_day()
        assert self.devices_page.find_query_status_text() == self.EDITED_QUERY_STATUS
        self.devices_page.discard_changes_query()
        self.devices_page.add_query_last_seen_next_day()
        assert self.devices_page.find_query_status_text() == self.EDITED_QUERY_STATUS
        self.devices_page.discard_changes_query()
        assert self.devices_page.find_query_status_text() == ''
        self.devices_page.click_sort_column(self.devices_page.FIELD_LAST_SEEN)
        assert self.devices_page.find_query_status_text() == self.EDITED_QUERY_STATUS
        self.devices_page.open_actions_query()
        self.devices_page.save_query_as(self.CUSTOM_QUERY_SAVE_NAME_2)
        assert self.devices_page.find_query_status_text() == ''
        assert self.devices_page.find_query_title_text() == self.CUSTOM_QUERY_SAVE_NAME_2
        self.devices_page.edit_columns(remove_col_names=[self.devices_page.FIELD_HOSTNAME_TITLE])
        assert self.devices_page.FIELD_HOSTNAME_TITLE not in self.devices_page.get_columns_header_text()
        assert self.devices_page.find_query_status_text() == self.EDITED_QUERY_STATUS
        self.devices_page.save_existing_query()
        wait_until(lambda: self.devices_page.find_query_status_text() == '')
        self.devices_page.reset_query()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.FIELD_HOSTNAME_TITLE in self.devices_page.get_columns_header_text()
        assert self.devices_page.count_entities() == 22
        self.devices_page.execute_saved_query(self.CUSTOM_QUERY_SAVE_NAME_2)
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.FIELD_HOSTNAME_TITLE not in self.devices_page.get_columns_header_text()
        assert self.devices_page.count_entities() == 21
        self.devices_page.check_sort_column(self.devices_page.FIELD_LAST_SEEN)

    @pytest.mark.skip('ad change')
    def test_enforcement_query(self):
        with DeviceControlService().contextmanager(take_ownership=True):
            self.dashboard_page.switch_to_page()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.build_query_active_directory()
            self.devices_page.save_query(self.CUSTOM_QUERY_SAVE_NAME_1)
            self.enforcements_page.switch_to_page()
            self.enforcements_page.create_deploying_enforcement(self.ENFORCEMENT_NAME, self.CUSTOM_QUERY_SAVE_NAME_1)
            self.base_page.run_discovery()
            self.enforcements_page.switch_to_page()
            self.enforcements_page.click_tasks_button()
            self.enforcements_page.wait_for_table_to_load()
            self.enforcements_page.wait_for_spinner_to_end()
            self.enforcements_page.navigate_task_success_results(self.ENFORCEMENT_NAME)
            self.devices_page.wait_for_table_to_load()
            assert self.devices_page.is_enforcement_results_header(self.ENFORCEMENT_NAME, self.ENFORCEMENT_NAME)
            tasks_results_count = self.devices_page.count_entities()
            self.devices_page.build_query_field_contains(self.devices_page.FIELD_HOSTNAME_TITLE, 'dc')
            assert self.devices_page.is_enforcement_results_header(self.ENFORCEMENT_NAME, self.ENFORCEMENT_NAME)
            assert self.devices_page.count_entities() < tasks_results_count
            self.devices_page.reset_query()
            assert not self.devices_page.is_enforcement_results_header(self.ENFORCEMENT_NAME, self.ENFORCEMENT_NAME)
            assert self.devices_page.find_query_title_text() == self.NEW_QUERY_TITLE
            self.enforcements_page.switch_to_page()
            self.enforcements_page.click_tasks_button()
            self.enforcements_page.wait_for_table_to_load()
            self.enforcements_page.wait_for_spinner_to_end()
            self.enforcements_page.navigate_task_success_results(self.ENFORCEMENT_NAME)
            self.devices_page.wait_for_table_to_load()
            assert self.devices_page.is_enforcement_results_header(self.ENFORCEMENT_NAME, self.ENFORCEMENT_NAME)
            self.devices_page.execute_saved_query(self.CUSTOM_QUERY_SAVE_NAME_1)
            assert self.devices_page.count_entities() > tasks_results_count

    def test_read_only_query(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, WINDOWS_QUERY_NAME)
        wait_until(lambda: self.devices_page.find_query_title_text() != self.NEW_QUERY_TITLE)
        self.devices_page.reset_query()
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_roles_settings()
        new_viewer_role = f'{uuid4().hex[:15]} viewer'
        new_viewer_permissions = copy.deepcopy(self.settings_page.VIEWER_PERMISSIONS)
        new_viewer_permissions['devices_assets'].append('Run saved queries')

        self.settings_page.create_new_role(new_viewer_role, new_viewer_permissions)
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(READ_ONLY_USERNAME, NEW_PASSWORD,
                                           role_name=new_viewer_role)
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=READ_ONLY_USERNAME, password=NEW_PASSWORD)
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.build_query_active_directory()
        self.devices_page.wait_for_table_to_be_responsive()
        assert not self.devices_page.is_query_save_as_disabled()
        self.devices_page.execute_saved_query(WINDOWS_QUERY_NAME)
        self.devices_page.click_sort_column(self.devices_page.FIELD_HOSTNAME_TITLE)
        assert self.devices_page.find_query_status_text() == self.EDITED_QUERY_STATUS
        assert self.devices_page.is_query_save_disabled()
        self.devices_page.open_actions_query()
        assert not self.devices_page.is_query_save_as_disabled()

    @pytest.mark.skip('ad change')
    def test_saved_queries_execute(self):
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, WINDOWS_QUERY_NAME)
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_LINUX, LINUX_QUERY_NAME)
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()

        self.devices_queries_page.switch_to_page()

        self.devices_page.wait_for_spinner_to_end()
        self.devices_queries_page.fill_enter_table_search('system')
        self.devices_queries_page.wait_for_spinner_to_end()
        windows_query_row = self.devices_queries_page.find_query_row_by_name(WINDOWS_QUERY_NAME)
        windows_query_row.click()
        self.devices_queries_page.run_query()
        assert 'devices' in self.driver.current_url and 'query' not in self.driver.current_url
        self.devices_page.wait_for_spinner_to_end()
        assert all(x == self.devices_page.VALUE_OS_WINDOWS for x in
                   self.devices_page.get_column_data_inline(self.devices_page.FIELD_OS_TYPE))
        self.devices_page.fill_filter('linux')
        self.devices_page.open_search_list()
        self.devices_page.select_query_by_name(LINUX_QUERY_NAME)
        self.devices_page.wait_for_spinner_to_end()
        assert not len(self.devices_page.get_column_data_inline(self.devices_page.FIELD_OS_TYPE))

    def test_saved_queries_remove(self):
        self.settings_page.switch_to_page()
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_load()
        self.devices_queries_page.wait_for_spinner_to_end()
        data_count = self.devices_queries_page.get_table_count()

        def _remove_queries_wait_count(data_count):
            self.devices_queries_page.remove_selected_queries(confirm=True)
            wait_until(lambda: self.devices_queries_page.get_table_count() == data_count)
            self.devices_page.wait_for_table_to_load()
            return data_count

        # Test remove a few (select each one)
        all_data = self.devices_queries_page.get_all_table_rows()
        self.devices_queries_page.click_row_checkbox(1)
        self.devices_queries_page.click_row_checkbox(2)
        self.devices_queries_page.click_row_checkbox(3)
        data_count = _remove_queries_wait_count(data_count - 3)
        current_data = self.devices_queries_page.get_all_table_rows()
        if len(current_data) == 20:
            current_data = current_data[:-3]
        assert current_data == all_data[3:]

        # Test remove all but some (select all and exclude 3 rows)
        all_data = self.devices_queries_page.get_all_table_rows()
        self.devices_queries_page.click_table_checkbox()
        self.devices_queries_page.click_row_checkbox(3)
        self.devices_queries_page.click_row_checkbox(6)
        self.devices_queries_page.click_row_checkbox(9)
        _remove_queries_wait_count(data_count - 17)
        assert self.devices_queries_page.get_all_table_rows()[:3] == [all_data[2], all_data[5], all_data[8]]

        # Test remove all
        self.devices_queries_page.click_table_checkbox()
        self.devices_queries_page.click_button('Select all')
        # test cancel remove
        self.devices_queries_page.remove_selected_queries()
        assert self.devices_queries_page.get_all_table_rows()[:3] == [all_data[2], all_data[5], all_data[8]]
        _remove_queries_wait_count(0)
        assert self.devices_queries_page.get_all_table_rows() == []

    @pytest.mark.skip('ad change')
    def test_saved_queries_search(self):
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, WINDOWS_QUERY_NAME)
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_load()
        self.devices_queries_page.wait_for_spinner_to_end()
        saved_queries_count = self.devices_queries_page.count_entities()
        self.devices_queries_page.fill_enter_table_search('operating system')
        self.devices_queries_page.wait_for_table_to_load()
        self.devices_queries_page.wait_for_spinner_to_end()
        for value in self.devices_queries_page.get_column_data_inline('Name'):
            assert 'operating system' in value.lower()
        assert self.devices_queries_page.count_entities() < saved_queries_count
        self.devices_queries_page.fill_enter_table_search('')
        self.devices_queries_page.wait_for_table_to_load()
        self.devices_queries_page.wait_for_spinner_to_end()
        assert self.devices_queries_page.count_entities() == saved_queries_count
        self.devices_page.switch_to_page()
        self.devices_page.execute_saved_query(WINDOWS_QUERY_NAME)
        for value in self.devices_page.get_column_data_inline(self.devices_page.FIELD_OS_TYPE):
            assert 'windows' in value.lower()

    def _test_predefined_queries(self):
        for value in self.devices_queries_page.get_column_data_inline(self.devices_queries_page.FIELD_UPDATED_BY):
            assert value == PREDEFINED_PLACEHOLDER
        assert self.devices_queries_page.get_column_data_inline(self.devices_queries_page.FIELD_LAST_UPDATED) == []

    def _test_admin_query(self, date_str):
        self.devices_page.switch_to_page()
        self.devices_page.run_filter_and_save(self.CUSTOM_QUERY_SAVE_NAME_1, self.devices_page.JSON_ADAPTER_FILTER)
        self._check_saved_query(self.CUSTOM_QUERY_SAVE_NAME_1, date_str, self.username, self.ADMIN_NAME)

    def _check_saved_query(self, query_name, date_str, username, first_name='', last_name=''):
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_load()
        self.devices_queries_page.wait_for_spinner_to_end()
        query_row = self.devices_queries_page.find_query_row_by_name(query_name)
        last_updated_cell_content = query_row.find_elements_by_css_selector('.table-td-last_updated div')[0].text
        assert date_str in normalize_timezone_date(last_updated_cell_content)

        username_cell = query_row.find_elements_by_css_selector('.table-td-updated_by div')[0]
        username_cell_content = username_cell.text
        user_name = f'internal/{username}'
        assert username_cell_content == user_name
        full_name = f'{first_name} {last_name}'.strip()
        expected_title = f'{user_name} - {full_name}' if full_name else user_name
        assert username_cell.get_attribute('title') == expected_title

    def _test_user_query(self, date_str):
        self.settings_page.create_new_user_with_new_permission(UPDATE_USERNAME, UPDATE_PASSWORD,
                                                               UPDATE_FIRST_NAME, UPDATE_LAST_NAME,
                                                               {
                                                                   'devices_assets': [
                                                                       'View devices',
                                                                       'Edit devices',
                                                                       'Run saved queries',
                                                                       'Edit saved queries',
                                                                       'Delete saved query',
                                                                       'Create saved query',
                                                                   ]
                                                               })
        self.login_page.switch_user(UPDATE_USERNAME, UPDATE_PASSWORD, '/devices')
        self._check_saved_query(self.CUSTOM_QUERY_SAVE_NAME_1, date_str, self.username, self.ADMIN_NAME)
        self.devices_page.switch_to_page()
        self.devices_page.run_filter_and_save(self.CUSTOM_QUERY_SAVE_NAME_2, self.devices_page.JSON_ADAPTER_FILTER)
        self._check_saved_query(self.CUSTOM_QUERY_SAVE_NAME_2, date_str, UPDATE_USERNAME,
                                UPDATE_FIRST_NAME, UPDATE_LAST_NAME)

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(self.username, self.password)
        self._check_saved_query(self.CUSTOM_QUERY_SAVE_NAME_2, date_str, UPDATE_USERNAME,
                                UPDATE_FIRST_NAME, UPDATE_LAST_NAME)

    def test_saved_query_update_fields(self):
        self.settings_page.switch_to_page()
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_load()
        self.devices_queries_page.wait_for_spinner_to_end()

        today_str = datetime.now().strftime('%Y-%m-%d')
        self._test_predefined_queries()
        self._test_admin_query(today_str)
        self._test_user_query(today_str)
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.click_edit_user(UPDATE_USERNAME)
        self.settings_page.fill_first_name('')
        self.settings_page.click_update_user()
        self._check_saved_query(self.CUSTOM_QUERY_SAVE_NAME_2, today_str, UPDATE_USERNAME, '', UPDATE_LAST_NAME)
        self.devices_queries_page.find_query_row_by_name(self.CUSTOM_QUERY_SAVE_NAME_2).click()
        self.devices_queries_page.run_query()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.fill_enter_table_search('test')
        self.devices_page.save_existing_query()
        self._check_saved_query(self.CUSTOM_QUERY_SAVE_NAME_2, today_str, self.username, self.ADMIN_NAME)

    def test_saved_query_with_entity_asset(self):
        self.adapters_page.add_json_extra_client()
        self.base_page.run_discovery()
        self.devices_page.build_asset_entity_query(JSON_ADAPTER_NAME,
                                                   self.devices_page.FIELD_HOSTNAME_TITLE,
                                                   DEVICE_FIRST_HOSTNAME,
                                                   self.devices_page.FIELD_ASSET_NAME,
                                                   DEVICE_SECOND_NAME)
        self.devices_page.click_search()
        self.devices_page.save_query(self.JSON_ASSET_ENTITY_QUERY_NAME)
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_be_responsive()
        self.devices_queries_page.fill_enter_table_search(self.JSON_ASSET_ENTITY_QUERY_NAME)
        self.devices_queries_page.find_query_row_by_name(self.JSON_ASSET_ENTITY_QUERY_NAME).click()
        self.devices_queries_page.run_query()

        self.devices_page.wait_for_table_to_load()
        assert len(self.devices_page.get_all_data()) == 1
        self.adapters_page.remove_json_extra_client()

    def test_predefined_queries_not_editable(self):
        saved_query_name = 'All installed software on devices'
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_be_responsive()
        self.devices_queries_page.click_query_row_by_name(saved_query_name)
        with pytest.raises(SeleniumTimeoutException):
            self.devices_queries_page.get_edit_panel_action()

    def test_predefined_queries_has_no_last_updated(self):
        saved_query_name = 'All installed software on devices'
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_be_responsive()
        self.devices_queries_page.click_query_row_by_name(saved_query_name)
        with pytest.raises(TimeoutException):
            self.devices_queries_page.get_query_last_update_from_panel()

    def test_generated_saved_query_in_table_and_panel(self):
        query_name = ''

        def get_actual_query_name():
            query_name = self.devices_queries_page.get_query_name_from_panel()
            return query_name != ''

        self.devices_page.switch_to_page()
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, WINDOWS_QUERY_NAME)
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_be_responsive()
        # assert query name
        assert self.devices_queries_page.get_row_cell_text(row_index=1, cell_index=2) == WINDOWS_QUERY_NAME
        # assert query last_update is not empty
        assert self.devices_queries_page.get_row_cell_text(row_index=1, cell_index=5)
        # assert query updater
        assert self.devices_queries_page.get_row_cell_text(row_index=1, cell_index=6) == self.ADMIN_DISPLAY_NAME

        self.devices_queries_page.click_query_row_by_name(WINDOWS_QUERY_NAME)

        wait_until(get_actual_query_name)

        assert self.devices_queries_page.get_query_name_from_panel() == WINDOWS_QUERY_NAME
        assert self.devices_queries_page\
                   .get_query_expression_eval_message() == self.devices_queries_page.NO_EXPRESSIONS_DEFINED_MSG
        assert self.devices_queries_page.get_edit_panel_action()
        assert self.devices_queries_page.get_enforce_panel_action()
        assert self.devices_queries_page.get_remove_panel_action()

    def test_unsupported_expression_msg(self):
        saved_query_name = 'All installed software on devices'
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_be_responsive()
        self.devices_queries_page.fill_enter_table_search(saved_query_name)
        self.devices_queries_page.wait_for_table_to_be_responsive()
        self.devices_queries_page.click_query_row_by_name(query_name=saved_query_name)
        assert self.devices_queries_page\
                   .get_query_expression_eval_message() == self.devices_queries_page.EXPRESSION_UNSUPPORTED_MSG
        self.devices_queries_page.close_saved_query_panel()

    @pytest.mark.skip('ad change')
    def test_saved_query_recompile(self):
        """
        Test that the predefined query that gets run from the saved queries page
        doesn't get recompiled if no changes were made and vice versa.
        1- Choose the 'Devices seen in last 7 days' from the saved queries page
           and check that it doesn't get recompiled when opening the wizard.
           Also make sure that if we change the expression, the query is edited
           and table is reloaded, and if we revert our change, there is no edit and reload.
        2- Choose the 'Devices seen in last 7 days' from the dropdown
           and check that it doesn't get recompiled when opening the wizard.
           Also make sure that if we change the expression, the query is edited
           and table is reloaded, and if we revert our change, there is no edit and reload.
        3- Change the 'Devices seen in last 7 days' filter and save the query
           ( This query's expression and filter doesn't match )
           Reset the query and then choose it from the list and check that it recompiles.
           That's because this query is NOT predefined and it SHOULD be recompiled due to the
           difference between the filter and the expression.
        """

        # Check 1
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_be_responsive()
        self.devices_queries_page.click_query_row_by_name(self.devices_page.AD_PREDEFINED_QUERY_NAME)
        self.devices_queries_page.run_query()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()
        assert self.devices_page.find_query_status_text() != self.EDITED_QUERY_STATUS
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_NEXT_DAYS)
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.find_query_status_text() == self.EDITED_QUERY_STATUS
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_DAYS)
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.find_query_status_text() != self.EDITED_QUERY_STATUS
        self.devices_page.click_search()

        # Check 2
        self.devices_page.switch_to_page()
        self.devices_page.execute_saved_query(self.devices_page.AD_PREDEFINED_QUERY_NAME)
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()
        assert self.devices_page.find_query_status_text() != self.EDITED_QUERY_STATUS
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_NEXT_DAYS)
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.find_query_status_text() == self.EDITED_QUERY_STATUS
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_DAYS)
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.find_query_status_text() != self.EDITED_QUERY_STATUS

        # Check 3
        self.devices_page.click_search()
        self.devices_page.fill_filter('random filter')
        self.devices_page.enter_search()
        self.devices_page.wait_for_table_to_load()
        query_save_name = 'user saved query'
        self.devices_page.open_actions_query()
        self.devices_page.save_query_as(query_save_name)
        self.devices_page.reset_query()
        self.devices_page.execute_saved_query(query_save_name)
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()
        assert self.devices_page.find_query_status_text() == self.EDITED_QUERY_STATUS

    def test_private_query(self):
        """
        Testing private query operations, including filtering and making sure it appears only
        on relevant pages with a series of checks:
        1 - Check private query operations for user with "admin" role.
        2 - Check private query operations for user with "viewer" role.
        3 - Check private query operations for user with "view_and_add" role. ( User can also add query )
        4 - Check that private query doesn't appear in: Reports, EC Config, Query Wizard, and also
            doesn't appear in any chart wizard opened from dashboard spaces besides "My Dashboard"
        5 - Check that private query appears in: Devices/Users query search input (inside the dropdown)
            And also appears in chart wizard at "My Dashboard"
        6 - Check that if a dashboard chart contains a private query, it cannot be moved/copied
            to any space besides "My Dashboard"
        """

        # Check 1:
        public_admin_query = self.PUBLIC_QUERY_SAVE_NAME.format(user_name='Admin')
        self.devices_page.create_private_query(self.INITIAL_QUERY_NAME)
        self.devices_page.assert_private_query_checkbox_hidden(self.INITIAL_QUERY_NAME)
        self.devices_page.rename_query(self.INITIAL_QUERY_NAME, public_admin_query)
        self._assert_private_query_created_and_renamed(public_admin_query)
        self._assert_private_query_set_public(public_admin_query)

        # Check 2:
        self._create_and_login_user(VIEWER_USERNAME, self.settings_page.VIEWER_PERMISSIONS)
        private_viewer_query = self.PRIVATE_QUERY_SAVE_NAME.format(user_name='Viewer')
        self.devices_page.create_private_query(self.INITIAL_QUERY_NAME)
        self.devices_page.rename_query(self.INITIAL_QUERY_NAME, private_viewer_query)
        self._assert_private_query_created_and_renamed(private_viewer_query)
        self.devices_queries_page.click_query_row_by_name(private_viewer_query)
        with pytest.raises(SeleniumTimeoutException):
            self.devices_queries_page.get_set_public_panel_action()
        assert self.devices_queries_page.get_edit_panel_action()
        self.devices_queries_page.get_remove_panel_action().click()
        self.devices_queries_page.safeguard_click_confirm(self.devices_queries_page.SAFEGUARD_REMOVE_BUTTON_SINGLE)
        self.devices_queries_page.wait_for_table_to_be_responsive()
        name_cell_index = self.devices_queries_page.count_sort_column(self.devices_queries_page.NAME_COLUMN)
        name = self.devices_queries_page.get_row_cell_text(1, name_cell_index)
        assert name != private_viewer_query
        self.devices_page.create_private_query(private_viewer_query)

        # Check 3:
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=DEFAULT_USER['user_name'], password=DEFAULT_USER['password'])
        self._create_and_login_user(VIEWER_ADDER_USERNAME, self.settings_page.VIEWER_ADDER_PERMISSIONS)
        public_viewer_adder_query = self.PUBLIC_QUERY_SAVE_NAME.format(user_name='Viewer Adder')
        private_viewer_adder_query = self.PRIVATE_QUERY_SAVE_NAME.format(user_name='Viewer Adder')
        self.devices_page.create_private_query(public_viewer_adder_query)
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_be_responsive()
        self._assert_private_query_set_public(public_viewer_adder_query)
        self.devices_page.create_private_query(private_viewer_adder_query)

        # Check 4:
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
        self.dashboard_page.switch_to_page()
        self.dashboard_page.open_new_card_wizard()
        self.dashboard_page.select_chart_metric('Query Comparison')
        self.devices_queries_page.assert_private_query_not_selectable(
            self.PRIVATE_QUERY_SAVE_NAME.format(user_name=''),
            self.devices_queries_page.SELECT_VIEW_NAME_CSS)

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
