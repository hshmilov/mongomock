import time

import pytest
from flaky import flaky
from selenium.common.exceptions import NoSuchElementException

from axonius.consts.metric_consts import SystemMetric
from ui_tests.tests.ui_test_base import TestBase
from test_credentials.json_file_credentials import client_details as json_file_creds


COMMON_ENFORCEMENT_QUERY = 'Enabled AD Devices'

ENFORCEMENT_CHANGE_NAME = 'test_enforcement_change'
ENFORCEMENT_CHANGE_FILTER = 'adapters_data.json_file_adapter.test_enforcement_change == 5'

FIELD_NAME = 'Name'
FIELD_QUERY_NAME = 'Trigger Query Name'

JSON_NAME = 'JSON File'


class TestEnforcementSanity(TestBase):
    def _create_enforcement_change_query(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.run_filter_and_save(ENFORCEMENT_CHANGE_NAME, ENFORCEMENT_CHANGE_FILTER)

    def test_enforcement_changing_triggers(self):
        self._create_enforcement_change_query()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.wait_for_spinner_to_end()
        self.enforcements_page.fill_enforcement_name(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_scheduling()
        self.enforcements_page.select_saved_view(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.save_trigger()
        self.enforcements_page.add_push_system_notification()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ENFORCEMENT_CHANGE_NAME)

        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.edit_enforcement(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_conditions()
        self.enforcements_page.check_below()
        self.enforcements_page.fill_below_value(1)
        self.enforcements_page.save_trigger()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        # make sure it is still 1
        self.notification_page.verify_amount_of_notifications(1)

        self.adapters_page.clean_adapter_servers(JSON_NAME)

        try:
            # Making the query return 0 results
            db = self.axonius_system.get_devices_db()
            result = db.update_one({'adapters.data.test_enforcement_change': 5},
                                   {'$set': {'adapters.$.data.test_enforcement_change': 4}})
            assert result.modified_count == 1
            self.base_page.run_discovery()
            # make sure it is now 2
            self.notification_page.verify_amount_of_notifications(2)

        finally:
            # restore JSON client
            self.adapters_page.add_server(json_file_creds, JSON_NAME)
            self.adapters_page.wait_for_server_green()
            self.adapters_page.wait_for_table_to_load()
            self.adapters_page.wait_for_data_collection_toaster_absent()

    def test_new(self):
        self.adapters_page.clean_adapter_servers(JSON_NAME)
        try:
            self._create_enforcement_change_query()
            self.enforcements_page.switch_to_page()
            self.enforcements_page.wait_for_table_to_load()
            self.enforcements_page.click_new_enforcement()
            self.enforcements_page.wait_for_spinner_to_end()
            self.enforcements_page.fill_enforcement_name(ENFORCEMENT_CHANGE_NAME)
            self.enforcements_page.select_trigger()
            self.enforcements_page.select_saved_view(ENFORCEMENT_CHANGE_NAME)
            self.enforcements_page.check_scheduling()
            self.enforcements_page.check_conditions()
            self.enforcements_page.check_condition_added()
            self.enforcements_page.save_trigger()
            self.enforcements_page.add_push_system_notification()
            self.enforcements_page.click_save_button()

            self.base_page.run_discovery()
            self.notification_page.verify_amount_of_notifications(0)
            assert self.axonius_system.gui.log_tester.is_metric_in_log(SystemMetric.ENFORCEMENT_RAW,
                                                                       ENFORCEMENT_CHANGE_NAME)
        finally:
            # restore JSON client
            self.adapters_page.add_server(json_file_creds, JSON_NAME)
            self.adapters_page.wait_for_server_green()
            self.adapters_page.wait_for_table_to_load()
            self.adapters_page.wait_for_data_collection_toaster_absent()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ENFORCEMENT_CHANGE_NAME)

    def test_save_query_deletion(self):
        self._create_enforcement_change_query()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.fill_enforcement_name(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_scheduling()
        self.enforcements_page.select_saved_view(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.save_trigger()
        self.enforcements_page.add_push_system_notification()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ENFORCEMENT_CHANGE_NAME)

        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_spinner_to_end()
        self.devices_queries_page.check_query_by_name(ENFORCEMENT_CHANGE_NAME)
        self.devices_queries_page.remove_selected_queries(confirm=True)
        self.driver.refresh()
        with pytest.raises(NoSuchElementException):
            self.devices_queries_page.find_query_row_by_name(ENFORCEMENT_CHANGE_NAME)

        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.edit_enforcement(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.select_saved_view(ENFORCEMENT_CHANGE_NAME)
        text = self.enforcements_page.get_saved_query_text()
        formatted = f'{ENFORCEMENT_CHANGE_NAME} (deleted)'
        assert text == formatted

    @flaky(max_runs=3)
    def test_edit_enforcement(self):
        self._create_enforcement_change_query()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.wait_for_spinner_to_end()
        self.enforcements_page.fill_enforcement_name(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_scheduling()
        self.enforcements_page.select_saved_view(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.check_conditions()
        self.enforcements_page.check_condition_subracted()
        self.enforcements_page.save_trigger()
        self.enforcements_page.add_push_system_notification()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(0)

        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.edit_enforcement(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        # uncheck Below
        self.enforcements_page.check_condition_subracted()
        self.enforcements_page.save_trigger()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        # make sure it is now 1
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ENFORCEMENT_CHANGE_NAME)

    def test_enforcement_table_sort(self):
        self._create_enforcement_change_query()
        self.enforcements_page.switch_to_page()
        enforcement_names = ['Test 3', 'Test 2', 'Test 5', 'Test 1', 'Test 4']
        enforcement_queries = [COMMON_ENFORCEMENT_QUERY, ENFORCEMENT_CHANGE_NAME, COMMON_ENFORCEMENT_QUERY,
                               ENFORCEMENT_CHANGE_NAME, ENFORCEMENT_CHANGE_NAME]
        for i, name in enumerate(enforcement_names):
            self.enforcements_page.create_notifying_enforcement(name, enforcement_queries[i])

        self.enforcements_page.click_sort_column(FIELD_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data(FIELD_NAME) == sorted(enforcement_names, reverse=True)
        self.enforcements_page.click_sort_column(FIELD_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data(FIELD_NAME) == sorted(enforcement_names)
        self.enforcements_page.click_sort_column(FIELD_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data(FIELD_NAME) == list(reversed(enforcement_names))

        self.enforcements_page.click_sort_column(FIELD_QUERY_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data(
            FIELD_QUERY_NAME) == sorted(enforcement_queries, reverse=True)
        self.enforcements_page.click_sort_column(FIELD_QUERY_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data(FIELD_QUERY_NAME) == sorted(enforcement_queries)
        self.enforcements_page.click_sort_column(FIELD_QUERY_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data(FIELD_QUERY_NAME) == list(reversed(enforcement_queries))

        # Default sort is according to update time
        for name in sorted(enforcement_names):
            self.enforcements_page.edit_enforcement(name)
            self.enforcements_page.click_save_button()
            self.enforcements_page.wait_for_table_to_load()
            # Make a distinct difference between each save
            time.sleep(1)
        assert self.enforcements_page.get_column_data(FIELD_NAME) == sorted(enforcement_names, reverse=True)

    def test_enforcement_table_search(self):
        self._create_enforcement_change_query()
        self.enforcements_page.switch_to_page()
        enforcement_names = ['Test 3', 'Test 2', 'Test 5', 'Test 1', 'Test 4']
        enforcement_queries = [COMMON_ENFORCEMENT_QUERY, ENFORCEMENT_CHANGE_NAME, COMMON_ENFORCEMENT_QUERY,
                               ENFORCEMENT_CHANGE_NAME, ENFORCEMENT_CHANGE_NAME]
        for i, name in enumerate(enforcement_names):
            self.enforcements_page.create_notifying_enforcement(name, enforcement_queries[i])

        self.enforcements_page.fill_enter_table_search('Test')
        self.enforcements_page.wait_for_table_to_load()
        assert len(self.enforcements_page.get_column_data(FIELD_NAME)) == 5
        self.enforcements_page.fill_enter_table_search('1')
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data(FIELD_NAME) == ['Test 1']
        self.enforcements_page.fill_enter_table_search(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data(FIELD_QUERY_NAME) == 3 * [ENFORCEMENT_CHANGE_NAME]

    def test_enforcement_triggers_order(self):
        self._create_enforcement_change_query()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.wait_for_spinner_to_end()
        self.enforcements_page.fill_enforcement_name(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_scheduling()
        labels = self.enforcements_page.get_all_periods_sorted()
        assert labels == ['Every Discovery Cycle', 'Daily', 'Weekly', 'Monthly']

    def test_enforcement_from_saved_query(self):
        self._create_enforcement_change_query()
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_load()
        self.devices_queries_page.wait_for_spinner_to_end()
        self.devices_queries_page.check_query_by_name(ENFORCEMENT_CHANGE_NAME)
        self.devices_queries_page.enforce_selected_query()

        self.enforcements_page.find_existing_trigger()
        self.enforcements_page.select_trigger()
        assert self.enforcements_page.get_saved_query_text() == ENFORCEMENT_CHANGE_NAME
