import datetime

import pytest
from selenium.common.exceptions import NoSuchElementException

from ui_tests.tests.ui_test_base import TestBase
from axonius.utils.wait import wait_until
from services.adapters.json_file_service import JsonFileService

ALERT_NAME = 'Special alert name'
ALERT_CHANGE_NAME = 'test_alert_change'


class TestAlert(TestBase):
    def test_new_alert_no_email_server(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_send_emails_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=False)
        self.settings_page.click_save_button()

        self.alert_page.switch_to_page()
        self.alert_page.click_new_alert()
        self.alert_page.fill_alert_name(ALERT_NAME)
        self.alert_page.wait_for_spinner_to_end()
        self.alert_page.click_send_an_email()
        self.alert_page.find_missing_email_server_notification()

    def test_remove_alert(self):
        self.create_outputting_notification_alert()

        self.base_page.run_discovery()
        assert self.notification_page.is_text_in_peek_notifications(ALERT_NAME)
        old_length = len(self.notification_page.get_peek_notifications())

        self.alert_page.switch_to_page()
        self.alert_page.wait_for_spinner_to_end()
        self.alert_page.wait_for_table_to_load()
        self.alert_page.select_all_alerts()
        self.alert_page.remove_selected_alerts()

        self.base_page.run_discovery()
        new_length = len(self.notification_page.get_peek_notifications())

        assert old_length == new_length

    def create_basic_alert(self):
        self.alert_page.switch_to_page()
        self.alert_page.click_new_alert()
        self.alert_page.wait_for_spinner_to_end()
        self.alert_page.fill_alert_name(ALERT_NAME)
        self.alert_page.select_saved_query('Enabled AD Devices')

    def create_outputting_notification_alert(self):
        self.create_basic_alert()
        self.alert_page.check_increased()
        self.alert_page.check_decreased()
        self.alert_page.check_not_changed()
        self.alert_page.check_push_system_notification()
        self.alert_page.click_save_button()

    def test_alert_timezone(self):
        self.create_outputting_notification_alert()
        self.base_page.run_discovery()
        self.notification_page.switch_to_page()
        wait_until(func=self.notification_page.get_rows_from_notification_table, total_timeout=60 * 5)
        rows = self.notification_page.get_rows_from_notification_table()
        timestamps = self.notification_page.get_timestamps_from_rows(rows)
        times = [self.notification_page.convert_timestamp_to_datetime(timestamp) for timestamp in timestamps]
        now = datetime.datetime.now()
        seconds_diff = [(now - single_time).total_seconds() for single_time in times]
        assert any(seconds < 60 * 5 for seconds in seconds_diff)

    def test_invalid_input(self):
        self.create_basic_alert()
        self.alert_page.check_increased()
        self.alert_page.fill_increased(-5)
        value = self.alert_page.get_increased_value()
        assert value == '5'

    def create_basic_saved_query(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.fill_filter('adapters_data.json_file_adapter.test_alert_change == 5')
        self.devices_page.enter_search()
        self.devices_page.click_save_query()
        self.devices_page.fill_query_name(ALERT_CHANGE_NAME)
        self.devices_page.click_save_query_save_button()

    def test_alert_changing_triggers(self):
        self.create_basic_saved_query()
        self.alert_page.switch_to_page()
        self.alert_page.wait_for_table_to_load()
        self.alert_page.click_new_alert()
        self.alert_page.wait_for_spinner_to_end()
        self.alert_page.fill_alert_name(ALERT_CHANGE_NAME)
        self.alert_page.select_saved_query(ALERT_CHANGE_NAME)
        self.alert_page.check_not_changed()
        self.alert_page.check_push_system_notification()
        self.alert_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ALERT_CHANGE_NAME)

        self.alert_page.wait_for_table_to_load()
        self.alert_page.edit_alert(ALERT_CHANGE_NAME)
        self.alert_page.wait_for_spinner_to_end()
        # uncheck Not Changed
        self.alert_page.check_not_changed()
        self.alert_page.check_decreased()
        self.alert_page.fill_decreased_value(1)
        self.alert_page.click_save_button()

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

    def test_increasing(self):
        json_service = JsonFileService()
        json_service.take_process_ownership()
        try:
            json_service.stop(should_delete=False)
            self.create_basic_saved_query()
            self.alert_page.switch_to_page()
            self.alert_page.wait_for_table_to_load()
            self.alert_page.click_new_alert()
            self.alert_page.wait_for_spinner_to_end()
            self.alert_page.fill_alert_name(ALERT_CHANGE_NAME)
            self.alert_page.select_saved_query(ALERT_CHANGE_NAME)
            self.alert_page.check_increased()
            self.alert_page.check_push_system_notification()
            self.alert_page.click_save_button()

            self.base_page.run_discovery()
            self.notification_page.verify_amount_of_notifications(0)
        finally:
            json_service.start_and_wait()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ALERT_CHANGE_NAME)

    def test_save_query_deletion(self):
        self.create_basic_saved_query()
        self.alert_page.switch_to_page()
        self.alert_page.wait_for_table_to_load()
        self.alert_page.click_new_alert()
        self.alert_page.wait_for_spinner_to_end()
        self.alert_page.fill_alert_name(ALERT_CHANGE_NAME)
        self.alert_page.select_saved_query(ALERT_CHANGE_NAME)
        self.alert_page.check_not_changed()
        self.alert_page.check_push_system_notification()
        self.alert_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ALERT_CHANGE_NAME)

        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_spinner_to_end()
        self.devices_queries_page.check_query_by_name(ALERT_CHANGE_NAME)
        self.devices_queries_page.remove_selected_queries()

        self.alert_page.switch_to_page()
        self.alert_page.wait_for_table_to_load()
        self.alert_page.edit_alert(ALERT_CHANGE_NAME)
        self.alert_page.wait_for_spinner_to_end()

        self.alert_page.select_saved_query(ALERT_CHANGE_NAME)
        text = self.alert_page.get_saved_query_text()
        formatted = f'{ALERT_CHANGE_NAME} (deleted)'
        assert text == formatted

    def test_delete_saved_query(self):
        self.create_basic_saved_query()
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_spinner_to_end()
        self.devices_queries_page.check_query_by_name(ALERT_CHANGE_NAME)
        self.devices_queries_page.remove_selected_queries()
        self.driver.refresh()
        with pytest.raises(NoSuchElementException):
            self.devices_queries_page.find_query_row_by_name(ALERT_CHANGE_NAME)

    def test_edit_alert(self):
        self.create_basic_saved_query()
        self.alert_page.switch_to_page()
        self.alert_page.wait_for_table_to_load()
        self.alert_page.click_new_alert()
        self.alert_page.wait_for_spinner_to_end()
        self.alert_page.fill_alert_name(ALERT_CHANGE_NAME)
        self.alert_page.select_saved_query(ALERT_CHANGE_NAME)
        self.alert_page.check_decreased()
        self.alert_page.check_push_system_notification()
        self.alert_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(0)

        self.alert_page.wait_for_table_to_load()
        self.alert_page.edit_alert(ALERT_CHANGE_NAME)
        self.alert_page.wait_for_spinner_to_end()
        # uncheck Decreased
        self.alert_page.check_decreased()
        self.alert_page.check_not_changed()
        self.alert_page.click_save_button()

        self.base_page.run_discovery()
        # make sure it is now 1
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ALERT_CHANGE_NAME)
