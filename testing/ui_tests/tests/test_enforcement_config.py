import time

from flaky import flaky

from axonius.consts.metric_consts import SystemMetric
from test_credentials.json_file_credentials import \
    client_details as json_file_creds
from ui_tests.tests.enforcement_config_base import TestEnforcementConfigBase
from ui_tests.tests.ui_consts import (JSON_ADAPTER_NAME,
                                      MANAGED_DEVICES_QUERY_NAME)


class TestEnforcementConfig(TestEnforcementConfigBase):
    VIEW_TASKS_CSS = '#view_tasks'

    def test_new(self):
        self.adapters_page.clean_adapter_servers(JSON_ADAPTER_NAME)
        self._create_enforcement_change_query()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.wait_for_spinner_to_end()
        self.enforcements_page.fill_enforcement_name(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.select_saved_view(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.check_scheduling()
        self.enforcements_page.check_conditions()
        self.enforcements_page.check_condition_added()
        self.enforcements_page.save_trigger()
        self.enforcements_page.add_push_system_notification()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(0)
        assert self.axonius_system.gui.log_tester.is_metric_in_log(SystemMetric.ENFORCEMENT_RAW,
                                                                   self.ENFORCEMENT_CHANGE_NAME)
        # restore JSON client
        self.adapters_page.add_server(json_file_creds, JSON_ADAPTER_NAME)
        self.adapters_page.wait_for_server_green()
        self.adapters_page.wait_for_table_to_load()
        self.adapters_page.wait_for_data_collection_toaster_absent()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(self.ENFORCEMENT_CHANGE_NAME)

    @flaky(max_runs=3)
    def test_edit_enforcement(self):
        self._create_enforcement_change_query()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.wait_for_spinner_to_end()
        self.enforcements_page.fill_enforcement_name(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_scheduling()
        self.enforcements_page.select_saved_view(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.check_conditions()
        self.enforcements_page.check_condition_subracted()
        self.enforcements_page.save_trigger()
        self.enforcements_page.add_push_system_notification()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(0)

        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_enforcement(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        # uncheck Below
        self.enforcements_page.check_condition_subracted()
        self.enforcements_page.save_trigger()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        # make sure it is now 1
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(self.ENFORCEMENT_CHANGE_NAME)

    def test_enforcement_table_sort(self):
        self._create_enforcement_change_query()
        self.enforcements_page.switch_to_page()
        enforcement_names = ['Test 3', 'Test 2', 'Test 5', 'Test 1', 'Test 4']
        enforcement_queries = [MANAGED_DEVICES_QUERY_NAME, self.ENFORCEMENT_CHANGE_NAME, MANAGED_DEVICES_QUERY_NAME,
                               self.ENFORCEMENT_CHANGE_NAME, self.ENFORCEMENT_CHANGE_NAME]
        for i, name in enumerate(enforcement_names):
            self.enforcements_page.create_notifying_enforcement(name, enforcement_queries[i])

        self.enforcements_page.click_sort_column(self.FIELD_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(self.FIELD_NAME) == sorted(enforcement_names, reverse=True)
        self.enforcements_page.click_sort_column(self.FIELD_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(self.FIELD_NAME) == sorted(enforcement_names)
        self.enforcements_page.click_sort_column(self.FIELD_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(self.FIELD_NAME) == list(reversed(enforcement_names))

        self.enforcements_page.click_sort_column(self.FIELD_QUERY_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(
            self.FIELD_QUERY_NAME) == sorted(enforcement_queries, reverse=True)
        self.enforcements_page.click_sort_column(self.FIELD_QUERY_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(self.FIELD_QUERY_NAME) == sorted(enforcement_queries)
        self.enforcements_page.click_sort_column(self.FIELD_QUERY_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(
            self.FIELD_QUERY_NAME) == list(reversed(enforcement_queries))

        # Default sort is according to update time
        for name in sorted(enforcement_names):
            self.enforcements_page.click_enforcement(name)
            self.enforcements_page.click_save_button()
            self.enforcements_page.wait_for_table_to_load()
            # Make a distinct difference between each save
            time.sleep(1)
        assert self.enforcements_page.get_column_data_inline(self.FIELD_NAME) == sorted(enforcement_names, reverse=True)

    def test_enforcement_from_saved_query(self):
        self._create_enforcement_change_query()
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_load()
        self.devices_queries_page.wait_for_spinner_to_end()
        self.devices_queries_page.find_query_row_by_name(self.ENFORCEMENT_CHANGE_NAME).click()
        self.devices_queries_page.enforce_selected_query()

        self.adapters_page.wait_for_element_absent_by_css(self.VIEW_TASKS_CSS)
        self.enforcements_page.find_existing_trigger()
        self.enforcements_page.select_trigger()
        assert self.enforcements_page.get_saved_query_text() == self.ENFORCEMENT_CHANGE_NAME
