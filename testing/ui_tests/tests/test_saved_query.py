from axonius.utils.wait import wait_until
from services.plugins.device_control_service import DeviceControlService
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests import ui_consts


class TestSavedQuery(TestBase):
    NEW_QUERY_TITLE = 'New Query'
    UNSAVED_QUERY_STATUS = '[Unsaved]'
    EDITED_QUERY_STATUS = '[Edited]'
    CUSTOM_QUERY_SAVE_NAME_1 = 'A Saved Query'
    CUSTOM_QUERY_SAVE_NAME_2 = 'Another Saved Query'
    CUSTOM_QUERY_SAVE_NAME_3 = 'Alternate Saved Query'
    ENFORCEMENT_NAME = 'An Enforcement'

    def test_query_state(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_query_title_text() == self.NEW_QUERY_TITLE
        assert self.devices_page.find_query_status_text() == self.UNSAVED_QUERY_STATUS
        self.devices_page.build_query_active_directory()
        self.devices_page.save_query(self.CUSTOM_QUERY_SAVE_NAME_1)
        assert self.devices_page.find_query_title_text() == self.CUSTOM_QUERY_SAVE_NAME_1
        self.devices_page.save_query_as(self.CUSTOM_QUERY_SAVE_NAME_2)
        assert self.devices_page.find_query_title_text() == self.CUSTOM_QUERY_SAVE_NAME_2
        self.devices_page.check_search_list_for_names([self.CUSTOM_QUERY_SAVE_NAME_1, self.CUSTOM_QUERY_SAVE_NAME_2])
        self.devices_page.rename_query(self.CUSTOM_QUERY_SAVE_NAME_2, self.CUSTOM_QUERY_SAVE_NAME_3)
        assert self.devices_page.find_query_title_text() == self.CUSTOM_QUERY_SAVE_NAME_3
        self.devices_page.check_search_list_for_names([self.CUSTOM_QUERY_SAVE_NAME_1, self.CUSTOM_QUERY_SAVE_NAME_3])
        assert self.devices_page.find_query_status_text() == ''
        self.devices_page.add_query_last_seen()
        assert self.devices_page.find_query_status_text() == self.EDITED_QUERY_STATUS

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
        self.devices_page.edit_columns([self.devices_page.FIELD_HOSTNAME_TITLE])
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
        self.settings_page.create_new_user(ui_consts.READ_ONLY_USERNAME, ui_consts.NEW_PASSWORD,
                                           role_name=self.settings_page.READ_ONLY_ROLE)
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=ui_consts.READ_ONLY_USERNAME, password=ui_consts.NEW_PASSWORD)
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.build_query_active_directory()
        assert self.devices_page.is_query_save_as_disabled()
        self.devices_page.execute_saved_query(self.devices_page.VALUE_SAVED_QUERY_WINDOWS)
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
        windows_query_row = self.devices_queries_page.find_query_row_by_name('Windows Operating System')
        self.devices_page.wait_for_spinner_to_end()
        windows_query_row.click()
        assert 'devices' in self.driver.current_url and 'query' not in self.driver.current_url
        self.devices_page.wait_for_spinner_to_end()
        assert all(x == self.devices_page.VALUE_OS_WINDOWS for x in
                   self.devices_page.get_column_data(self.devices_page.FIELD_OS_TYPE))
        self.devices_page.fill_filter('linux')
        self.devices_page.open_search_list()
        self.devices_page.select_query_by_name('Linux Operating System')
        self.devices_page.wait_for_spinner_to_end()
        assert not len(self.devices_page.get_column_data(self.devices_page.FIELD_OS_TYPE))

    def test_saved_queries_remove(self):
        self.settings_page.switch_to_page()
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_load()
        self.devices_queries_page.wait_for_spinner_to_end()
        data_count = self.devices_queries_page.get_table_count()

        def _remove_queries_wait_count(data_count):
            self.devices_queries_page.remove_selected_queries()
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
        _remove_queries_wait_count(0)
        assert self.devices_queries_page.get_all_table_rows() == []
