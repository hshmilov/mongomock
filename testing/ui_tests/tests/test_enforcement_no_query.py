import time
from datetime import datetime

import pytest
from selenium.common.exceptions import NoSuchElementException
from services.adapters.carbonblack_response_service import CarbonblackResponseService

from axonius.consts.metric_consts import SystemMetric
from axonius.utils.wait import wait_until
from axonius.utils.parsing import normalize_timezone_date
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.pages.enforcements_page import ActionCategory, Action

ENFORCEMENT_NAME = 'Special enforcement name'
COMMON_ENFORCEMENT_QUERY = 'Enabled AD Devices'

ENFORCEMENT_CHANGE_NAME = 'test_enforcement_change'
ENFORCEMENT_CHANGE_FILTER = 'adapters_data.json_file_adapter.test_enforcement_change == 5'

ENFORCEMENT_NUMBER_OF_DEVICES = 21
DUPLICATE_ACTION_NAME_ERROR = 'Name already taken by another saved Action'

SUCCESS_TAG_NAME = 'Tag Special Success'
FAILURE_TAG_NAME = 'Tag Special Failure'
FAILURE_ISOLATE_NAME = 'Isolate Special Failure'
POST_PUSH_NAME = 'Push Special Post'

FIELD_TIMES_TRIGGERED = 'Times Triggered'
FIELD_NAME = 'Name'
FIELD_QUERY_NAME = 'Trigger Query Name'
FIELD_LAST_TRIGGERED = 'Last Triggered'


class TestEnforcementNoQuery(TestBase):
    def test_remove_enforcement(self):
        self.enforcements_page.create_notifying_enforcement(ENFORCEMENT_NAME, COMMON_ENFORCEMENT_QUERY)
        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.notification_page.is_text_in_peek_notifications(ENFORCEMENT_NAME)
        old_length = len(self.notification_page.get_peek_notifications())

        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.select_all_enforcements()
        assert self.enforcements_page.count_entities() == 1
        self.enforcements_page.remove_selected_enforcements()
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.count_entities() == 1
        self.enforcements_page.remove_selected_enforcements(confirm=True)

        self.base_page.run_discovery()
        new_length = len(self.notification_page.get_peek_notifications())
        assert old_length == new_length

    def test_enforcement_invalid(self):
        self.enforcements_page.create_basic_enforcement(ENFORCEMENT_NAME, COMMON_ENFORCEMENT_QUERY, save=False)
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
        self.enforcements_page.remove_selected_enforcements(confirm=True)
        self.enforcements_page.create_basic_enforcement(duplicate_name, COMMON_ENFORCEMENT_QUERY)
        self.enforcements_page.add_push_system_notification(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.click_save_button()

    def test_above_threshold(self):
        self.enforcements_page.create_notifying_enforcement_above('above 1',
                                                                  COMMON_ENFORCEMENT_QUERY,
                                                                  above=ENFORCEMENT_NUMBER_OF_DEVICES + 10)

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(0)

        self.enforcements_page.create_notifying_enforcement_above('above 2',
                                                                  COMMON_ENFORCEMENT_QUERY,
                                                                  above=ENFORCEMENT_NUMBER_OF_DEVICES - 10)

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.axonius_system.gui.log_tester.is_metric_in_log(SystemMetric.ENFORCEMENT_RAW,
                                                                   COMMON_ENFORCEMENT_QUERY)

    def test_below_threshold(self):
        self.enforcements_page.create_notifying_enforcement_below('below 1',
                                                                  COMMON_ENFORCEMENT_QUERY,
                                                                  below=ENFORCEMENT_NUMBER_OF_DEVICES - 10)

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(0)

        self.enforcements_page.create_notifying_enforcement_below('below 2',
                                                                  COMMON_ENFORCEMENT_QUERY,
                                                                  below=ENFORCEMENT_NUMBER_OF_DEVICES + 10)

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)
        assert self.axonius_system.gui.log_tester.is_metric_in_log(SystemMetric.ENFORCEMENT_RAW,
                                                                   COMMON_ENFORCEMENT_QUERY)

    def test_no_scheduling(self):
        self.enforcements_page.create_basic_enforcement(
            ENFORCEMENT_CHANGE_NAME, COMMON_ENFORCEMENT_QUERY, schedule=False)
        self.enforcements_page.add_push_system_notification()
        self.enforcements_page.click_save_button()
        self.base_page.run_discovery()
        time.sleep(1)
        self.notification_page.verify_amount_of_notifications(0)
        assert '0' in self.enforcements_page.get_column_data(FIELD_TIMES_TRIGGERED)
        self.enforcements_page.edit_enforcement(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.click_run_button()
        # Save and Run does not exit the Enforcement Configuration Page
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.notification_page.verify_amount_of_notifications(1)
        wait_until(lambda: '1' in self.enforcements_page.get_column_data(FIELD_TIMES_TRIGGERED), interval=1)

    def test_enforcement_table_content(self):
        self.enforcements_page.create_notifying_enforcement(ENFORCEMENT_NAME, COMMON_ENFORCEMENT_QUERY)

        # Check initial state of Enforcement in table
        assert ENFORCEMENT_NAME in self.enforcements_page.get_column_data(FIELD_NAME)
        assert COMMON_ENFORCEMENT_QUERY in self.enforcements_page.get_column_data(FIELD_QUERY_NAME)
        assert '' in self.enforcements_page.get_column_data(FIELD_LAST_TRIGGERED)
        assert '0' in self.enforcements_page.get_column_data(FIELD_TIMES_TRIGGERED)

        self.base_page.run_discovery()
        self.enforcements_page.refresh()
        self.enforcements_page.wait_for_table_to_load()

        # Check triggered state of Enforcement in table
        assert ENFORCEMENT_NAME in self.enforcements_page.get_column_data(FIELD_NAME)
        assert COMMON_ENFORCEMENT_QUERY in self.enforcements_page.get_column_data(FIELD_QUERY_NAME)
        assert datetime.now().strftime('%Y-%m-%d') in normalize_timezone_date(
            self.enforcements_page.get_column_data(FIELD_LAST_TRIGGERED)[0])
        assert '1' in self.enforcements_page.get_column_data(FIELD_TIMES_TRIGGERED)

    def test_coming_soon(self):
        self.enforcements_page.switch_to_page()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.open_action_category(ActionCategory.Scan)
        # Opening animation time
        time.sleep(0.2)
        assert self.enforcements_page.find_disabled_action(Action.scan_with_qualys.value)

    def test_full_action_flow(self):
        """
        Test an Enforcement containing a Main action as well as success, failure and post actions
        """
        with CarbonblackResponseService().contextmanager(take_ownership=True):
            self.enforcements_page.create_deploying_enforcement(ENFORCEMENT_NAME, COMMON_ENFORCEMENT_QUERY)
            wait_until(lambda: self.enforcements_page.add_deploying_consequences(ENFORCEMENT_NAME, SUCCESS_TAG_NAME,
                                                                                 FAILURE_TAG_NAME,
                                                                                 FAILURE_ISOLATE_NAME),
                       tolerated_exceptions_list=[NoSuchElementException], total_timeout=60 * 5,
                       check_return_value=False)
            self.enforcements_page.edit_enforcement(ENFORCEMENT_NAME)
            self.enforcements_page.add_push_notification(POST_PUSH_NAME, self.enforcements_page.POST_ACTIONS_TEXT)
            self.enforcements_page.click_save_button()
            self.enforcements_page.wait_for_table_to_load()

            self.base_page.run_discovery()
            self.notification_page.verify_amount_of_notifications(1)

    def test_run_added_entities(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.delete_devices(self.devices_page.JSON_ADAPTER_FILTER)
        self.devices_page.run_filter_and_save(ENFORCEMENT_CHANGE_NAME, ENFORCEMENT_CHANGE_FILTER)

        self.enforcements_page.switch_to_page()
        self.enforcements_page.create_basic_enforcement(ENFORCEMENT_NAME, ENFORCEMENT_CHANGE_NAME, enforce_added=True)
        self.enforcements_page.add_tag_entities()
        self.enforcements_page.click_save_button()
        self.enforcements_page.wait_for_table_to_load()
        self.base_page.run_discovery()

        self.devices_page.switch_to_page()
        self.devices_page.run_filter_query('labels == "Special"')
        assert self.devices_page.count_entities() == 1
        assert 'CB 1' in self.devices_page.get_column_data(self.devices_page.FIELD_ASSET_NAME)

    def test_added_entities_trigger(self):
        """
        Verify that an enforcement using the Trigger condition 'New entities were added to results' will not be
        triggered again if no new results
        """
        self.enforcements_page.switch_to_page()
        self.enforcements_page.create_notifying_enforcement(ENFORCEMENT_NAME, COMMON_ENFORCEMENT_QUERY, added=True)
        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)

        self.base_page.run_discovery()
        self.notification_page.verify_amount_of_notifications(1)

    def test_action_library_search(self):
        """
        Verify that the search input in the action library is returning only action categories holding actions
        whose names contain the search value
        """
        self.enforcements_page.switch_to_page()
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.wait_for_action_library()
        self.enforcements_page.fill_action_library_search('de')
        assert self.enforcements_page.get_action_categories() == [ActionCategory.Deploy, ActionCategory.Isolate,
                                                                  ActionCategory.Enrichment,
                                                                  ActionCategory.Block, ActionCategory.ManageAD,
                                                                  ActionCategory.Incident]
        assert self.enforcements_page.get_action_category_items(ActionCategory.Isolate) == [
            Action.cybereason_isolate.value,
            Action.cybereason_unisolate.value,
            Action.carbonblack_defense_change_policy.value]
