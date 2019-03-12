from datetime import datetime

from axonius.utils.parsing import normalize_timezone_date
from services.plugins.device_control_service import DeviceControlService
from ui_tests.tests.ui_test_base import TestBase

ENFORCEMENT_NAME = 'Special enforcement name'
ENFORCEMENT_QUERY = 'Enabled AD Devices'

SUCCESS_TAG_NAME = 'Tag Special Success'
FAILURE_TAG_NAME = 'Tag Special Failure'
FAILURE_ISOLATE_NAME = 'Isolate Special Failure'


class TestTasks(TestBase):

    FIELD_ENFORCEMENT = 'Name'
    FIELD_MAIN_ACTION = 'Main Action'
    FIELD_QUERY_NAME = 'Trigger Query Name'
    FIELD_COMPLETED = 'Completed'

    def test_tasks_table(self):
        self.enforcements_page.create_deploying_enforcement(ENFORCEMENT_NAME, ENFORCEMENT_QUERY)
        self.enforcements_page.add_deploying_consequences(ENFORCEMENT_NAME, SUCCESS_TAG_NAME,
                                                          FAILURE_TAG_NAME, FAILURE_ISOLATE_NAME)
        self.base_page.run_discovery()
        self.enforcements_page.refresh()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_tasks_button()
        self.enforcements_page.wait_for_table_to_load()

        # Check Enforcement's Task details in table
        assert ENFORCEMENT_NAME in self.enforcements_page.get_column_data(self.FIELD_ENFORCEMENT)
        assert ENFORCEMENT_NAME in self.enforcements_page.get_column_data(self.FIELD_MAIN_ACTION)
        assert ENFORCEMENT_QUERY in self.enforcements_page.get_column_data(self.FIELD_QUERY_NAME)
        assert datetime.now().strftime('%Y-%m-%d') in normalize_timezone_date(
            self.enforcements_page.get_column_data(self.FIELD_COMPLETED)[0])

    def _check_action_result(self, result_element, entities_count, action_name=ENFORCEMENT_NAME):
        assert result_element.text == str(entities_count)
        result_element.click()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == entities_count
        assert self.devices_page.find_enforcement_results_header(ENFORCEMENT_NAME, action_name)
        assert 'exists_in(' in self.devices_page.find_search_value()
        self.devices_page.page_back()

    def _check_action_results(self, success_count, failure_count, action_name=ENFORCEMENT_NAME):
        self._check_action_result(
            self.enforcements_page.find_task_action_success(action_name), success_count, action_name)
        self._check_action_result(
            self.enforcements_page.find_task_action_failure(action_name), failure_count, action_name)

    def test_task_results(self):
        with DeviceControlService().contextmanager(take_ownership=True):
            self.enforcements_page.create_deploying_enforcement(ENFORCEMENT_NAME, ENFORCEMENT_QUERY)
            self.enforcements_page.add_deploying_consequences(ENFORCEMENT_NAME, SUCCESS_TAG_NAME,
                                                              FAILURE_TAG_NAME, FAILURE_ISOLATE_NAME)

            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            self.settings_page.click_toggle_button(self.settings_page.find_execution_toggle(), make_yes=True)
            self.settings_page.save_and_wait_for_toaster()
            self.base_page.run_discovery()

            self.enforcements_page.switch_to_page()
            self.enforcements_page.click_tasks_button()
            self.enforcements_page.click_row()

            self._check_action_results(12, 8)
            self._check_action_results(12, 0, SUCCESS_TAG_NAME)
            self._check_action_results(8, 0, FAILURE_TAG_NAME)
            self._check_action_results(0, 8, FAILURE_ISOLATE_NAME)
