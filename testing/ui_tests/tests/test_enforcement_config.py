import time
from datetime import datetime

import pytest
from flaky import flaky
from selenium.common.exceptions import NoSuchElementException

from axonius.consts.metric_consts import SystemMetric
from axonius.utils.wait import wait_until
from axonius.utils.parsing import normalize_timezone_date
from services.adapters.json_file_service import JsonFileService
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.pages.enforcements_page import ActionCategory, Action

ENFORCEMENT_NAME = 'Special enforcement name'
COMMON_ENFORCEMENT_QUERY = 'Enabled AD Devices'

ENFORCEMENT_CHANGE_NAME = 'test_enforcement_change'
ENFORCEMENT_CHANGE_FILTER = 'adapters_data.json_file_adapter.test_enforcement_change == 5'

ENFORCEMENT_NUMBER_OF_DEVICES = 21
DUPLICATE_ACTION_NAME_ERROR = 'Name already taken by another saved Action'


class TestEnforcementSanity(TestBase):

    FIELD_TIMES_TRIGGERED = 'Times Triggered'
    FIELD_NAME = 'Name'
    FIELD_MAIN_ACTION = 'Main Action'
    FIELD_QUERY_NAME = 'Trigger Query Name'
    FIELD_LAST_TRIGGERED = 'Last Triggered'

    def _create_enforcement_change_query(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.run_filter_and_save(ENFORCEMENT_CHANGE_NAME, ENFORCEMENT_CHANGE_FILTER)

    def test_remove_enforcement(self):
        self.enforcements_page.create_notifying_enforcement(ENFORCEMENT_NAME, COMMON_ENFORCEMENT_QUERY)
        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ENFORCEMENT_NAME)
        old_length = len(self.notification_page.get_peek_notifications())

        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.select_all_enforcements()
        self.enforcements_page.remove_selected_enforcements()

        self.base_page.run_discovery()
        new_length = len(self.notification_page.get_peek_notifications())
        assert old_length == new_length

    def test_enforcement_invalid(self):
        self.enforcements_page.create_basic_enforcement(ENFORCEMENT_NAME, COMMON_ENFORCEMENT_QUERY)
        self.enforcements_page.select_trigger()
        self.enforcements_page.check_conditions()

        # Check negative values
        self.enforcements_page.check_above()
        self.enforcements_page.fill_above_value(-5)
        value = self.enforcements_page.get_above_value()
        assert value == '5'

        # Check disallow duplicate action names
        self.enforcements_page.add_push_system_notification(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.click_save_button()
        duplicate_name = f'{ENFORCEMENT_NAME} Duplicate'
        self.enforcements_page.create_basic_enforcement(duplicate_name, COMMON_ENFORCEMENT_QUERY)
        with pytest.raises(NoSuchElementException):
            self.enforcements_page.add_push_system_notification(ENFORCEMENT_CHANGE_NAME)
        assert self.enforcements_page.find_element_by_text(DUPLICATE_ACTION_NAME_ERROR)
        self.enforcements_page.fill_action_name(f'{ENFORCEMENT_CHANGE_NAME} Duplicate')
        self.enforcements_page.save_action()
        self.enforcements_page.click_save_button()

        # Check remove enforcement allows re-use of names
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_row_checkbox(2)
        self.enforcements_page.remove_selected()
        self.enforcements_page.create_basic_enforcement(duplicate_name, COMMON_ENFORCEMENT_QUERY)
        self.enforcements_page.add_push_system_notification(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.click_save_button()

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

        json_service = JsonFileService()
        json_service.take_process_ownership()
        json_service.stop(should_delete=False)

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
            json_service.start_and_wait()

    def test_new(self):
        json_service = JsonFileService()
        json_service.take_process_ownership()
        try:
            json_service.stop(should_delete=False)
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
            self.enforcements_page.check_new()
            self.enforcements_page.save_trigger()
            self.enforcements_page.add_push_system_notification()
            self.enforcements_page.click_save_button()

            self.base_page.run_discovery()
            self.notification_page.verify_amount_of_notifications(0)
            self.axonius_system.gui.log_tester.is_metric_in_log(SystemMetric.ENFORCEMENT_RAW, ENFORCEMENT_CHANGE_NAME)
        finally:
            json_service.start_and_wait()

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
        self.devices_queries_page.remove_selected_queries()

        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.edit_enforcement(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        self.enforcements_page.select_saved_view(ENFORCEMENT_CHANGE_NAME)
        text = self.enforcements_page.get_saved_query_text()
        formatted = f'{ENFORCEMENT_CHANGE_NAME} (deleted)'
        assert text == formatted

    def test_delete_saved_query(self):
        self._create_enforcement_change_query()
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_spinner_to_end()
        self.devices_queries_page.check_query_by_name(ENFORCEMENT_CHANGE_NAME)
        self.devices_queries_page.remove_selected_queries()
        self.driver.refresh()
        with pytest.raises(NoSuchElementException):
            self.devices_queries_page.find_query_row_by_name(ENFORCEMENT_CHANGE_NAME)

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
        self.enforcements_page.check_previous()
        self.enforcements_page.save_trigger()
        self.enforcements_page.add_push_system_notification()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(0)

        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.edit_enforcement(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.select_trigger()
        # uncheck Below
        self.enforcements_page.check_previous()
        self.enforcements_page.save_trigger()
        self.enforcements_page.click_save_button()

        self.base_page.run_discovery()
        # make sure it is now 1
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ENFORCEMENT_CHANGE_NAME)

    def test_above_threshold(self):
        self.enforcements_page.create_outputting_notification_above('above 1',
                                                                    COMMON_ENFORCEMENT_QUERY,
                                                                    above=ENFORCEMENT_NUMBER_OF_DEVICES + 10)

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(0)

        self.enforcements_page.create_outputting_notification_above('above 2',
                                                                    COMMON_ENFORCEMENT_QUERY,
                                                                    above=ENFORCEMENT_NUMBER_OF_DEVICES - 10)

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        self.axonius_system.gui.log_tester.is_metric_in_log(SystemMetric.ENFORCEMENT_RAW, COMMON_ENFORCEMENT_QUERY)

    def test_below_threshold(self):
        self.enforcements_page.create_outputting_notification_below('below 1',
                                                                    COMMON_ENFORCEMENT_QUERY,
                                                                    below=ENFORCEMENT_NUMBER_OF_DEVICES - 10)

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(0)

        self.enforcements_page.create_outputting_notification_below('below 2',
                                                                    COMMON_ENFORCEMENT_QUERY,
                                                                    below=ENFORCEMENT_NUMBER_OF_DEVICES + 10)

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        self.axonius_system.gui.log_tester.is_metric_in_log(SystemMetric.ENFORCEMENT_RAW, COMMON_ENFORCEMENT_QUERY)

    def test_no_scheduling(self):
        self.enforcements_page.create_basic_enforcement(
            ENFORCEMENT_CHANGE_NAME, COMMON_ENFORCEMENT_QUERY, schedule=False)
        self.enforcements_page.add_push_system_notification()
        self.enforcements_page.click_save_button()
        self.base_page.run_discovery()
        time.sleep(1)
        self.notification_page.verify_amount_of_notifications(0)
        assert '0' in self.enforcements_page.get_column_data(self.FIELD_TIMES_TRIGGERED)
        self.enforcements_page.edit_enforcement(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.click_run_button()
        self.notification_page.verify_amount_of_notifications(1)
        wait_until(lambda: '1' in self.enforcements_page.get_column_data(self.FIELD_TIMES_TRIGGERED))

    def test_enforcement_table(self):
        self.enforcements_page.create_notifying_enforcement(ENFORCEMENT_NAME, COMMON_ENFORCEMENT_QUERY)
        self.enforcements_page.wait_for_table_to_load()

        # Check initial state of Enforcement in table
        assert ENFORCEMENT_NAME in self.enforcements_page.get_column_data(self.FIELD_NAME)
        assert COMMON_ENFORCEMENT_QUERY in self.enforcements_page.get_column_data(self.FIELD_QUERY_NAME)
        assert '' in self.enforcements_page.get_column_data(self.FIELD_LAST_TRIGGERED)
        assert '0' in self.enforcements_page.get_column_data(self.FIELD_TIMES_TRIGGERED)

        self.base_page.run_discovery()
        self.enforcements_page.refresh()
        self.enforcements_page.wait_for_table_to_load()

        # Check triggered state of Enforcement in table
        assert ENFORCEMENT_NAME in self.enforcements_page.get_column_data(self.FIELD_NAME)
        assert COMMON_ENFORCEMENT_QUERY in self.enforcements_page.get_column_data(self.FIELD_QUERY_NAME)
        assert datetime.now().strftime('%Y-%m-%d') in normalize_timezone_date(
            self.enforcements_page.get_column_data(self.FIELD_LAST_TRIGGERED)[0])
        assert '1' in self.enforcements_page.get_column_data(self.FIELD_TIMES_TRIGGERED)

    def test_coming_soon(self):
        self.enforcements_page.switch_to_page()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.open_action_category(ActionCategory.Scan)
        # Opening animation time
        time.sleep(0.2)
        assert self.enforcements_page.find_disabled_action(Action.ScanQualys)
        assert self.enforcements_page.find_disabled_action(Action.ScanTenable)
