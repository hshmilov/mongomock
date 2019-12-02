from datetime import datetime

from axonius.utils.wait import wait_until
from axonius.utils.parsing import normalize_timezone_date
from axonius.consts.gui_consts import PREDEFINED_PLACEHOLDER
from services.plugins.device_control_service import DeviceControlService
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import (READ_ONLY_USERNAME, NEW_PASSWORD,
                                      UPDATE_USERNAME, UPDATE_PASSWORD, UPDATE_FIRST_NAME, UPDATE_LAST_NAME,
                                      WINDOWS_QUERY_NAME)


class TestSavedQuery(TestBase):
    NEW_QUERY_TITLE = 'New Query'
    UNSAVED_QUERY_STATUS = '[Unsaved]'
    EDITED_QUERY_STATUS = '[Edited]'
    CUSTOM_QUERY_SAVE_NAME_1 = 'A Saved Query'
    CUSTOM_QUERY_SAVE_NAME_2 = 'Another Saved Query'
    CUSTOM_QUERY_SAVE_NAME_3 = 'Alternate Saved Query'
    ENFORCEMENT_NAME = 'An Enforcement'

    ADMIN_NAME = 'administrator'

    def test_query_state(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_query_title_text() == self.NEW_QUERY_TITLE
        assert self.devices_page.find_query_status_text() == self.UNSAVED_QUERY_STATUS
        assert self.devices_page.is_query_save_disabled()

        # Save is enabled when user changes: Filter \ Columns \ Sort \ Column Filters
        self.devices_page.build_query_active_directory()
        assert not self.devices_page.is_query_save_disabled()
        # Remove host name field
        self.devices_page.edit_columns(remove_col_names=[self.devices_page.FIELD_TAGS])
        assert not self.devices_page.is_query_save_disabled()
        self.devices_page.fill_enter_table_search('')
        assert not self.devices_page.is_query_save_disabled()
        # Add host name field
        self.devices_page.edit_columns(add_col_names=[self.devices_page.FIELD_TAGS])
        assert self.devices_page.is_query_save_disabled()
        # Sort host name field
        self.devices_page.click_sort_column(self.devices_page.FIELD_HOSTNAME_TITLE)
        assert not self.devices_page.is_query_save_disabled()
        # No sort host name field
        self.devices_page.click_sort_column(self.devices_page.FIELD_HOSTNAME_TITLE)
        self.devices_page.click_sort_column(self.devices_page.FIELD_HOSTNAME_TITLE)
        assert self.devices_page.is_query_save_disabled()
        # Filter host name field
        self.devices_page.filter_column(self.devices_page.FIELD_HOSTNAME_TITLE, 'test')
        assert not self.devices_page.is_query_save_disabled()
        # No filter host name field
        self.devices_page.filter_column(self.devices_page.FIELD_HOSTNAME_TITLE, '')
        assert self.devices_page.is_query_save_disabled()
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
        self.devices_page.add_query_last_seen()
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
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(READ_ONLY_USERNAME, NEW_PASSWORD,
                                           role_name=self.settings_page.READ_ONLY_ROLE)
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=READ_ONLY_USERNAME, password=NEW_PASSWORD)
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.build_query_active_directory()
        assert self.devices_page.is_query_save_as_disabled()
        self.devices_page.execute_saved_query(WINDOWS_QUERY_NAME)
        self.devices_page.click_sort_column(self.devices_page.FIELD_HOSTNAME_TITLE)
        assert self.devices_page.find_query_status_text() == self.EDITED_QUERY_STATUS
        assert self.devices_page.is_query_save_disabled()
        self.devices_page.open_actions_query()
        assert self.devices_page.is_query_save_as_disabled()

    def test_saved_queries_execute(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()

        self.devices_queries_page.switch_to_page()

        self.devices_page.wait_for_spinner_to_end()
        self.devices_queries_page.fill_enter_table_search('system')
        windows_query_row = self.devices_queries_page.find_query_row_by_name(WINDOWS_QUERY_NAME)
        self.devices_page.wait_for_spinner_to_end()
        windows_query_row.click()
        assert 'devices' in self.driver.current_url and 'query' not in self.driver.current_url
        self.devices_page.wait_for_spinner_to_end()
        assert all(x == self.devices_page.VALUE_OS_WINDOWS for x in
                   self.devices_page.get_column_data_inline(self.devices_page.FIELD_OS_TYPE))
        self.devices_page.fill_filter('linux')
        self.devices_page.open_search_list()
        self.devices_page.select_query_by_name('Linux Operating System')
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
        self.devices_queries_page.click_button('Select all', partial_class=True)
        # test cancel remove
        self.devices_queries_page.remove_selected_queries()
        assert self.devices_queries_page.get_all_table_rows()[:3] == [all_data[2], all_data[5], all_data[8]]
        _remove_queries_wait_count(0)
        assert self.devices_queries_page.get_all_table_rows() == []

    def test_saved_queries_search(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_load()
        self.devices_queries_page.wait_for_spinner_to_end()
        saved_queries_count = self.devices_queries_page.count_entities()
        self.devices_queries_page.fill_enter_table_search('operating system')
        for value in self.devices_queries_page.get_column_data_inline('Name'):
            assert 'operating system' in value.lower()
        assert self.devices_queries_page.count_entities() < saved_queries_count
        self.devices_queries_page.fill_enter_table_search('')
        self.devices_queries_page.wait_for_table_to_load()
        assert self.devices_queries_page.count_entities() == saved_queries_count
        self.devices_page.switch_to_page()
        self.devices_page.execute_saved_query(WINDOWS_QUERY_NAME)
        for value in self.devices_page.get_column_data_inline(self.devices_page.FIELD_OS_TYPE):
            assert 'windows' in value.lower()

    def _test_predefined_queries(self, date_str):
        for value in self.devices_queries_page.get_column_data_inline(self.devices_queries_page.FIELD_UPDATED_BY):
            assert value == PREDEFINED_PLACEHOLDER
        for value in self.devices_queries_page.get_column_data_inline(self.devices_queries_page.FIELD_LAST_UPDATED):
            assert date_str in normalize_timezone_date(value)

    def _test_admin_query(self, date_str):
        self.devices_page.switch_to_page()
        self.devices_page.run_filter_and_save(self.CUSTOM_QUERY_SAVE_NAME_1, self.devices_page.JSON_ADAPTER_FILTER)
        self._check_saved_query(self.CUSTOM_QUERY_SAVE_NAME_1, date_str, self.username, self.ADMIN_NAME)

    def _check_saved_query(self, query_name, date_str, username, first_name='', last_name=''):
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_load()
        self.devices_queries_page.wait_for_spinner_to_end()
        query_row_cells = self.devices_queries_page.find_query_row_by_name(query_name).find_elements_by_css_selector(
            'td:not(.top) div')
        assert date_str in normalize_timezone_date(query_row_cells[1].text)
        user_name = f'internal/{username}'
        assert query_row_cells[2].text == user_name
        full_name = f'{first_name} {last_name}'.strip()
        expected_title = f'{user_name} - {full_name}' if full_name else user_name
        assert query_row_cells[2].get_attribute('title') == expected_title

    def _test_user_query(self, date_str):
        self.settings_page.add_user_with_permission(UPDATE_USERNAME, UPDATE_PASSWORD,
                                                    UPDATE_FIRST_NAME, UPDATE_LAST_NAME,
                                                    'Devices', self.settings_page.READ_WRITE_PERMISSION)
        self.login_page.switch_user(UPDATE_USERNAME, UPDATE_PASSWORD)
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

        today_str = datetime.now().isoformat()[:10]
        self._test_predefined_queries(today_str)
        self._test_admin_query(today_str)
        self._test_user_query(today_str)
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.click_edit_user(UPDATE_USERNAME)
        self.settings_page.fill_text_field_by_element_id('first_name', '')
        self.settings_page.click_update_user()
        self._check_saved_query(self.CUSTOM_QUERY_SAVE_NAME_2, today_str, UPDATE_USERNAME, '', UPDATE_LAST_NAME)
        self.devices_queries_page.find_query_row_by_name(self.CUSTOM_QUERY_SAVE_NAME_2).click()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.fill_enter_table_search('test')
        self.devices_page.save_existing_query()
        self._check_saved_query(self.CUSTOM_QUERY_SAVE_NAME_2, today_str, self.username, self.ADMIN_NAME)
