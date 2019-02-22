import time

import pytest
from flaky import flaky
from selenium.common.exceptions import NoSuchElementException

from axonius.consts.metric_consts import SystemMetric
from services.adapters.json_file_service import JsonFileService
from ui_tests.tests.ui_test_base import TestBase

ALERT_NAME = 'Special alert name'
COMMON_ALERT_QUERY = 'Enabled AD Devices'

ALERT_CHANGE_NAME = 'test_alert_change'
ALERT_CHANGE_FILTER = 'adapters_data.json_file_adapter.test_alert_change == 5'

ALERT_NUMBER_OF_DEVICES = 21


class TestAlertSanity(TestBase):
    def create_alert_change_query(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        # sometimes it appears like we are directed to the dashboard at this stage
        self.devices_page.switch_to_page()
        self.devices_page.run_filter_and_save(ALERT_CHANGE_NAME, ALERT_CHANGE_FILTER)

    def test_remove_alert(self):
        # Added to wait for another discovery that happens at the beginning before adding the alert.
        time.sleep(10)
        self.base_page.wait_for_run_research()

        self.enforcements_page.create_notifying_enforcement(ALERT_NAME, COMMON_ALERT_QUERY)
        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ALERT_NAME)
        old_length = len(self.notification_page.get_peek_notifications())

        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_spinner_to_end()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.select_all_alerts()
        self.enforcements_page.remove_selected_alerts()

        self.base_page.run_discovery()
        new_length = len(self.notification_page.get_peek_notifications())

        assert old_length == new_length

    def test_invalid_input(self):
        self.enforcements_page.create_basic_enforcement(ALERT_NAME, COMMON_ALERT_QUERY)
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_above()
        self.enforcements_page.fill_above_value(-5)
        value = self.enforcements_page.get_above_value()
        assert value == '5'

    def test_alert_changing_triggers(self):
        self.create_alert_change_query()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.wait_for_spinner_to_end()
        self.enforcements_page.fill_enforcement_name(ALERT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_scheduling()
        self.enforcements_page.select_saved_view(ALERT_CHANGE_NAME)
        self.enforcements_page.save_trigger()
        self.enforcements_page.add_push_system_notification()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ALERT_CHANGE_NAME)

        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.edit_enforcement(ALERT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_below()
        self.enforcements_page.fill_below_value(1)
        self.enforcements_page.save_trigger()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        # make sure it is still 1
        self.notification_page.verify_amount_of_notifications(1)

        json_service = JsonFileService()
        json_service.take_process_ownership()
        json_service.stop(should_delete=False)

        try:
            # Making the query return 0 results
            db = self.axonius_system.get_devices_db()
            result = db.update_one({'adapters.data.test_alert_change': 5},
                                   {'$set': {'adapters.$.data.test_alert_change': 4}})
            assert result.modified_count == 1
            self.base_page.run_discovery()
            # make sure it is now 2
            self.notification_page.verify_amount_of_notifications(2)

        finally:
            json_service.start_and_wait()

    def test_new(self):
        json_service = JsonFileService()
        json_service.take_process_ownership()
        try:
            json_service.stop(should_delete=False)
            self.create_alert_change_query()
            self.enforcements_page.switch_to_page()
            self.enforcements_page.wait_for_table_to_load()
            self.enforcements_page.click_new_enforcement()
            self.enforcements_page.wait_for_spinner_to_end()
            self.enforcements_page.fill_enforcement_name(ALERT_CHANGE_NAME)
            self.enforcements_page.select_trigger()
            self.enforcements_page.select_saved_view(ALERT_CHANGE_NAME)
            self.enforcements_page.check_scheduling()
            self.enforcements_page.check_new()
            self.enforcements_page.save_trigger()
            self.enforcements_page.add_push_system_notification()
            self.enforcements_page.click_save_button()

            self.base_page.run_discovery()
            self.notification_page.verify_amount_of_notifications(0)
            self.axonius_system.gui.log_tester.is_metric_in_log(SystemMetric.ALERT_RAW, ALERT_CHANGE_NAME)
        finally:
            json_service.start_and_wait()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ALERT_CHANGE_NAME)

    def test_save_query_deletion(self):
        self.create_alert_change_query()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.wait_for_spinner_to_end()
        self.enforcements_page.fill_enforcement_name(ALERT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_scheduling()
        self.enforcements_page.select_saved_view(ALERT_CHANGE_NAME)
        self.enforcements_page.save_trigger()
        self.enforcements_page.add_push_system_notification()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ALERT_CHANGE_NAME)

        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_spinner_to_end()
        self.devices_queries_page.check_query_by_name(ALERT_CHANGE_NAME)
        self.devices_queries_page.remove_selected_queries()

        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.edit_enforcement(ALERT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.select_saved_view(ALERT_CHANGE_NAME)
        text = self.enforcements_page.get_saved_query_text()
        formatted = f'{ALERT_CHANGE_NAME} (deleted)'
        assert text == formatted

    def test_delete_saved_query(self):
        self.create_alert_change_query()
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_spinner_to_end()
        self.devices_queries_page.check_query_by_name(ALERT_CHANGE_NAME)
        self.devices_queries_page.remove_selected_queries()
        self.driver.refresh()
        with pytest.raises(NoSuchElementException):
            self.devices_queries_page.find_query_row_by_name(ALERT_CHANGE_NAME)

    @flaky(max_runs=3)
    def test_edit_alert(self):
        self.create_alert_change_query()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.wait_for_spinner_to_end()
        self.enforcements_page.fill_enforcement_name(ALERT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_scheduling()
        self.enforcements_page.select_saved_view(ALERT_CHANGE_NAME)
        self.enforcements_page.check_previous()
        self.enforcements_page.save_trigger()
        self.enforcements_page.add_push_system_notification()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(0)

        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.edit_enforcement(ALERT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        # uncheck Below
        self.enforcements_page.check_previous()
        self.enforcements_page.save_trigger()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        # make sure it is now 1
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ALERT_CHANGE_NAME)

    def test_above_threshold(self):
        self.enforcements_page.create_outputting_notification_above('above 1',
                                                                    COMMON_ALERT_QUERY,
                                                                    above=ALERT_NUMBER_OF_DEVICES + 10)

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(0)

        self.enforcements_page.create_outputting_notification_above('above 2',
                                                                    COMMON_ALERT_QUERY,
                                                                    above=ALERT_NUMBER_OF_DEVICES - 10)

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        self.axonius_system.gui.log_tester.is_metric_in_log(SystemMetric.ALERT_RAW, COMMON_ALERT_QUERY)

    def test_below_threshold(self):
        self.enforcements_page.create_outputting_notification_below('below 1',
                                                                    COMMON_ALERT_QUERY,
                                                                    below=ALERT_NUMBER_OF_DEVICES - 10)

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(0)

        self.enforcements_page.create_outputting_notification_below('below 2',
                                                                    COMMON_ALERT_QUERY,
                                                                    below=ALERT_NUMBER_OF_DEVICES + 10)

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        self.axonius_system.gui.log_tester.is_metric_in_log(SystemMetric.ALERT_RAW, COMMON_ALERT_QUERY)
