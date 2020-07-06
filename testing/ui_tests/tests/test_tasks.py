import time
from datetime import datetime

from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from axonius.utils.parsing import normalize_timezone_date
from axonius.utils.wait import wait_until
from services.adapters.carbonblack_response_service import \
    CarbonblackResponseService
from services.adapters.wmi_service import WmiService
from testing.test_credentials.test_ad_credentials import (NONEXISTEN_AD_DEVICE_IP,
                                                          WMI_QUERIES_DEVICE)
from ui_tests.tests.ui_consts import Enforcements
from ui_tests.tests.ui_test_base import TestBase

ENFORCEMENT_NAME = 'Special enforcement name'
ENFORCEMENT_QUERY = 'Run WMI task'
ENFORCEMENT_CHANGE_NAME = 'test_enforcement_change'
ENFORCEMENT_DEVICES_QUERY = f'adapters_data.active_directory_adapter.hostname == "{WMI_QUERIES_DEVICE}" or ' \
    f'adapters_data.active_directory_adapter.network_interfaces.ips == "{NONEXISTEN_AD_DEVICE_IP}"'
ENFORCEMENT_CHANGE_FILTER = 'adapters_data.json_file_adapter.test_enforcement_change == 5'
TEST_ENFORCEMENT_NAME = 'Test 1'

SUCCESS_TAG_NAME = 'Tag Special Success'
FAILURE_TAG_NAME = 'Tag Special Failure'
FAILURE_ISOLATE_NAME = 'Isolate Special Failure'
CUSTOM_TAG = 'TestTag'
ACTION_NAME = 'TestAction'


class TestTasks(TestBase):

    FIELD_MAIN_ACTION = 'Main Action'
    FIELD_QUERY_NAME = 'Trigger Query Name'

    def _check_enforcement_data(self):
        # Check Enforcement's Task details in table
        assert f'{ENFORCEMENT_NAME} - Task 1'\
               in self.enforcements_page.get_column_data_inline(self.enforcements_page.FIELD_NAME)
        assert ENFORCEMENT_NAME in self.enforcements_page.get_column_data_inline(self.FIELD_MAIN_ACTION)
        assert ENFORCEMENT_QUERY in self.enforcements_page.get_column_data_inline(self.FIELD_QUERY_NAME)
        assert datetime.now().strftime('%Y-%m-%d') in normalize_timezone_date(
            self.enforcements_page.get_column_data_inline(self.enforcements_page.FIELD_COMPLETED)[0])

    def test_tasks_table_content(self):
        with CarbonblackResponseService().contextmanager(take_ownership=True):
            self.devices_page.switch_to_page()
            self.devices_page.run_filter_and_save(ENFORCEMENT_QUERY, ENFORCEMENT_DEVICES_QUERY)
            self.enforcements_page.create_deploying_enforcement(ENFORCEMENT_NAME, ENFORCEMENT_QUERY)
            wait_until(lambda: self.enforcements_page.add_deploying_consequences(ENFORCEMENT_NAME, SUCCESS_TAG_NAME,
                                                                                 FAILURE_TAG_NAME,
                                                                                 FAILURE_ISOLATE_NAME),
                       tolerated_exceptions_list=[NoSuchElementException], total_timeout=60 * 5,
                       check_return_value=False)
            self.base_page.run_discovery()
            self.enforcements_page.refresh()
            self.enforcements_page.wait_for_table_to_load()
            self.enforcements_page.click_tasks_button()

            wait_until(self._check_enforcement_data, check_return_value=False,
                       tolerated_exceptions_list=[StaleElementReferenceException])

    def _check_action_result(self, result_element, entities_count, action_name=ENFORCEMENT_NAME):
        assert result_element.text == str(entities_count)
        result_element.click()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == entities_count
        assert self.devices_page.is_enforcement_results_header(ENFORCEMENT_NAME, action_name)
        assert 'exists_in(' in self.devices_page.find_search_value()
        self.devices_page.page_back()

    def _check_action_results(self, success_count, failure_count, action_name=ENFORCEMENT_NAME):
        self._check_action_result(
            self.enforcements_page.find_task_action_success(action_name), success_count, action_name)
        time.sleep(1)
        self._check_action_result(
            self.enforcements_page.find_task_action_failure(action_name), failure_count, action_name)

    def test_tasks_table_sort(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.run_filter_and_save(ENFORCEMENT_CHANGE_NAME, ENFORCEMENT_CHANGE_FILTER)
        self.devices_page.run_filter_and_save(ENFORCEMENT_QUERY, ENFORCEMENT_DEVICES_QUERY)

        self.enforcements_page.switch_to_page()
        enforcement_names = ['Test 3', 'Test 2', 'Test 5', 'Test 1', 'Test 4']
        query_names = [ENFORCEMENT_QUERY, ENFORCEMENT_CHANGE_NAME, ENFORCEMENT_QUERY,
                       ENFORCEMENT_CHANGE_NAME, ENFORCEMENT_CHANGE_NAME]
        for i, name in enumerate(enforcement_names):
            self.enforcements_page.create_notifying_enforcement(name, query_names[i],
                                                                added=False, subtracted=False)
        self.base_page.run_discovery()
        self.enforcements_page.click_tasks_button()

        self.enforcements_page.click_sort_column(self.enforcements_page.FIELD_STATUS)
        self.enforcements_page.wait_for_table_to_load()
        original_order = self.enforcements_page.get_column_data_inline(self.enforcements_page.FIELD_NAME)
        self.enforcements_page.click_sort_column(self.enforcements_page.FIELD_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(
            self.enforcements_page.FIELD_NAME) == sorted(original_order, reverse=True)
        self.enforcements_page.click_sort_column(self.enforcements_page.FIELD_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(
            self.enforcements_page.FIELD_NAME) == sorted(original_order)
        self.enforcements_page.click_sort_column(self.enforcements_page.FIELD_STATUS)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(self.enforcements_page.FIELD_NAME) == original_order

        original_order = self.enforcements_page.get_column_data_inline(self.FIELD_QUERY_NAME)
        self.enforcements_page.click_sort_column(self.FIELD_QUERY_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(self.FIELD_QUERY_NAME) == sorted(query_names, reverse=True)
        self.enforcements_page.click_sort_column(self.FIELD_QUERY_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(self.FIELD_QUERY_NAME) == sorted(query_names)
        self.enforcements_page.click_sort_column(self.enforcements_page.FIELD_STATUS)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(self.FIELD_QUERY_NAME) == original_order

    def test_tasks_table_search(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.run_filter_and_save(ENFORCEMENT_CHANGE_NAME, ENFORCEMENT_CHANGE_FILTER)
        self.devices_page.run_filter_and_save(ENFORCEMENT_QUERY, ENFORCEMENT_DEVICES_QUERY)

        self.enforcements_page.switch_to_page()
        enforcement_names = ['Test 3', 'Test 2', 'Test 5', 'Test 1', 'Test 4']
        query_names = [ENFORCEMENT_QUERY, ENFORCEMENT_CHANGE_NAME, ENFORCEMENT_QUERY,
                       ENFORCEMENT_CHANGE_NAME, ENFORCEMENT_CHANGE_NAME]
        for i, name in enumerate(enforcement_names):
            self.enforcements_page.create_notifying_enforcement(name, query_names[i],
                                                                added=False, subtracted=False)
        self.base_page.run_discovery()
        self.enforcements_page.click_tasks_button()

        self.enforcements_page.fill_enter_table_search('Test')
        self.enforcements_page.wait_for_table_to_load()
        assert len(self.enforcements_page.get_column_data_inline(self.enforcements_page.FIELD_NAME)) == 5

        self.enforcements_page.fill_enter_table_search(TEST_ENFORCEMENT_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert TEST_ENFORCEMENT_NAME in self.enforcements_page.get_enforcement_table_task_name()

        self.enforcements_page.fill_enter_table_search(ENFORCEMENT_CHANGE_NAME)
        self.enforcements_page.wait_for_table_to_load()
        assert self.enforcements_page.get_column_data_inline(self.FIELD_QUERY_NAME) == 3 * [ENFORCEMENT_CHANGE_NAME]

        self.enforcements_page.fill_enter_table_search('In Progress')
        self.enforcements_page.wait_for_table_to_load()
        assert len(self.enforcements_page.get_column_data_inline(self.enforcements_page.FIELD_NAME)) == 0

    def _test_specific_task(self, success_count, failure_count, action_name=ENFORCEMENT_NAME):
        self.enforcements_page.switch_to_page()
        self.enforcements_page.refresh()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_tasks_button()
        self.enforcements_page.click_row()  # raises StaleElementReferenceException
        # After specific task page finishes loading it jumps back to show data about the main action.
        # So this sleeps make sure that we don't select an action just to be shown
        # again the main action task info after the pages "OnLoad".
        time.sleep(2)
        self.enforcements_page.select_task_action(action_name)
        self._check_action_results(success_count, failure_count, action_name)

    def test_task_results(self):
        with WmiService().contextmanager(take_ownership=True), CarbonblackResponseService().contextmanager(
                take_ownership=True):
            # restart gui service for master instance to be available at node selection.
            # should be deleted when AX-4451 is done
            gui_service = self.axonius_system.gui
            gui_service.take_process_ownership()
            gui_service.stop(should_delete=False)
            gui_service.start_and_wait()
            time.sleep(5)
            self.login()

            self.devices_page.switch_to_page()
            self.devices_page.run_filter_and_save(ENFORCEMENT_QUERY, ENFORCEMENT_DEVICES_QUERY)
            self.enforcements_page.create_deploying_enforcement(ENFORCEMENT_NAME, ENFORCEMENT_QUERY)
            wait_until(lambda: self.enforcements_page.add_deploying_consequences(ENFORCEMENT_NAME, SUCCESS_TAG_NAME,
                                                                                 FAILURE_TAG_NAME,
                                                                                 FAILURE_ISOLATE_NAME),
                       tolerated_exceptions_list=[NoSuchElementException], total_timeout=60 * 5,
                       check_return_value=False)

            self.base_page.run_discovery()

            time.sleep(2)

            self._test_specific_task(1, 1)
            self._test_specific_task(1, 0, SUCCESS_TAG_NAME)
            self._test_specific_task(1, 0, FAILURE_TAG_NAME)
            self._test_specific_task(0, 1, FAILURE_ISOLATE_NAME)

    def test_enforcement_tasks(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.run_filter_and_save(ENFORCEMENT_CHANGE_NAME, ENFORCEMENT_CHANGE_FILTER)
        self.devices_page.run_filter_and_save(ENFORCEMENT_QUERY, ENFORCEMENT_DEVICES_QUERY)

        self.enforcements_page.switch_to_page()
        self.enforcements_page.create_notifying_enforcement('Test 1', ENFORCEMENT_CHANGE_NAME,
                                                            added=False, subtracted=False)
        self.enforcements_page.create_notifying_enforcement('Test 2', ENFORCEMENT_QUERY,
                                                            added=False, subtracted=False)
        self.base_page.run_discovery()
        self.enforcements_page.click_enforcement('Test 1')
        self.enforcements_page.click_tasks_button()

        assert len(self.enforcements_page.get_all_data()) == 1
        assert self.enforcements_page.get_column_data_inline(self.FIELD_QUERY_NAME) == [ENFORCEMENT_CHANGE_NAME]

        self.enforcements_page.refresh()
        self.enforcements_page.wait_for_spinner_to_end()
        self.enforcements_page.wait_for_table_to_load()
        assert len(self.enforcements_page.get_all_data()) == 2
        assert ENFORCEMENT_QUERY in self.enforcements_page.get_column_data_inline(self.FIELD_QUERY_NAME)[0]

    def test_enforcement_task_query_change(self):
        query_name = Enforcements.enforcement_query_1
        enforcement_name = TEST_ENFORCEMENT_NAME
        action_name = ACTION_NAME

        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, query_name)
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.base_page.run_discovery()

        # create new task to add custom tag to all windows based devices
        self.enforcements_page.click_new_enforcement()
        self.enforcements_page.fill_enforcement_name(enforcement_name)
        self.enforcements_page.select_trigger()
        self.enforcements_page.select_saved_view(query_name)
        self.enforcements_page.save_trigger()
        self.enforcements_page.add_push_system_notification(action_name)
        self.enforcements_page.add_tag_entities(enforcement_name, CUSTOM_TAG,
                                                self.enforcements_page.POST_ACTIONS_TEXT)
        self.enforcements_page.click_run_button()
        self.enforcements_page.wait_for_task_in_progress_toaster()
        self.notification_page.wait_for_count(1)
        self.enforcements_page.switch_to_page()
        self.enforcements_page.fill_enter_table_search(enforcement_name)
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_row()
        self.enforcements_page.click_tasks_button()

        self.enforcements_page.wait_until_enforcement_task_completion()
        task_name = self.enforcements_page.get_enforcement_table_task_name()
        self.enforcements_page.click_row()
        self.enforcements_page.click_result_redirect()

        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_query_title_text() == task_name

        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_be_responsive()
        self.devices_queries_page.click_query_row_by_name(query_name)
        self.devices_queries_page.wait_for_side_panel()
        self.devices_queries_page.run_query()
        assert self.devices_page.find_query_title_text() == query_name
