import pytest
from selenium.common.exceptions import NoSuchElementException

from ui_tests.tests.enforcement_config_base import TestEnforcementConfigBase
from ui_tests.tests.ui_consts import MANAGED_DEVICES_QUERY_NAME, JSON_ADAPTER_NAME
from test_credentials.json_file_credentials import client_details as json_file_creds


class TestEnforcementMoreConfigs(TestEnforcementConfigBase):

    def test_enforcement_triggers_order(self):
        self._create_enforcement_change_query()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.wait_for_spinner_to_end()
        self.enforcements_page.fill_enforcement_name(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_scheduling()
        labels = self.enforcements_page.get_all_periods_sorted()
        assert labels == self.RECURRENCE_OPTIONS

    def test_enforcement_table_search(self):
        self._create_enforcement_change_query()
        self.enforcements_page.switch_to_page()
        enforcement_names = ['Test 3', 'Test 2', 'Test 5', 'Test 1', 'Test 4']
        enforcement_queries = [MANAGED_DEVICES_QUERY_NAME, self.ENFORCEMENT_CHANGE_NAME, MANAGED_DEVICES_QUERY_NAME,
                               self.ENFORCEMENT_CHANGE_NAME, self.ENFORCEMENT_CHANGE_NAME]
        for i, name in enumerate(enforcement_names):
            self.enforcements_page.create_notifying_enforcement(name, enforcement_queries[i])

        self.enforcements_page.fill_enter_table_search('Test')
        self.enforcements_page.wait_for_table_to_load()
        assert len(self.enforcements_page.get_column_data_inline(self.FIELD_NAME)) == 5
        self.enforcements_page.fill_enter_table_search('1')
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(self.FIELD_NAME) == ['Test 1']
        self.enforcements_page.fill_enter_table_search(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(self.FIELD_QUERY_NAME) == 3 * [
            self.ENFORCEMENT_CHANGE_NAME]

    def test_save_query_deletion(self):
        self._create_enforcement_change_query()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.fill_enforcement_name(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_scheduling()
        self.enforcements_page.select_saved_view(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.save_trigger()
        self.enforcements_page.add_push_system_notification()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(self.ENFORCEMENT_CHANGE_NAME)

        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_spinner_to_end()
        self.devices_queries_page.check_query_by_name(self.ENFORCEMENT_CHANGE_NAME)
        self.devices_queries_page.remove_selected_queries(confirm=True)
        self.driver.refresh()
        with pytest.raises(NoSuchElementException):
            self.devices_queries_page.find_query_row_by_name(self.ENFORCEMENT_CHANGE_NAME)

        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_enforcement(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        text = self.enforcements_page.get_saved_query_text()
        # Currently only id appear for the deleted query, rather than its name
        # formatted = f'{ENFORCEMENT_CHANGE_NAME} (deleted)'
        assert 'deleted' in text

    def test_enforcement_changing_triggers(self):
        self._create_enforcement_change_query()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.wait_for_spinner_to_end()
        self.enforcements_page.fill_enforcement_name(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_scheduling()
        self.enforcements_page.select_saved_view(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.save_trigger()
        self.enforcements_page.add_push_system_notification()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(self.ENFORCEMENT_CHANGE_NAME)

        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_enforcement(self.ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_conditions()
        self.enforcements_page.check_below()
        self.enforcements_page.fill_below_value(1)
        self.enforcements_page.save_trigger()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        # make sure it is still 1
        self.notification_page.verify_amount_of_notifications(1)

        self.adapters_page.clean_adapter_servers(JSON_ADAPTER_NAME)

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
            self.adapters_page.add_server(json_file_creds, JSON_ADAPTER_NAME)
            self.adapters_page.wait_for_server_green()
            self.adapters_page.wait_for_table_to_load()
            self.adapters_page.wait_for_data_collection_toaster_absent()
