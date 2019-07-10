# pylint: disable=too-many-statements
import time

from axonius.utils.wait import wait_until
from services.plugins.device_control_service import DeviceControlService
from test_credentials.test_ad_credentials import WMI_QUERIES_DEVICE
from ui_tests.pages.enforcements_page import Action
from ui_tests.tests.ui_test_base import TestBase

RUN_CMD_ENFORCEMENT_NAME = 'Run Cmd Enforcement'
RUN_CMD_ACTION_NAME = 'Run Windows Command'

# Files which are uploaded remotely must be named 'axonius_' because we have a mechanism that deletes them
# after a day in case they were not deleted automatically.
CONSTANT_PREFIX = 'axonius_'
FIRST_FILE_NAME = 'first_file_name'
SECOND_FILE_NAME = 'second_file_name'
FIRST_FILE_CONTENTS = 'first-file-contents'
SECOND_FILE_CONTENTS = 'second-file-contents'


class TestEnforcementExecution(TestBase):
    def test_run_cmd_with_files(self):
        with DeviceControlService().contextmanager(take_ownership=True):
            self.base_page.run_discovery()
            self.enforcements_page.create_basic_empty_enforcement(RUN_CMD_ENFORCEMENT_NAME)
            current_prefix = CONSTANT_PREFIX + str(time.time()) + '_'
            full_first_file_name = f'{current_prefix}_{FIRST_FILE_NAME}'
            full_second_file_name = f'{current_prefix}_{SECOND_FILE_NAME}'
            self.enforcements_page.add_run_windows_command(
                RUN_CMD_ACTION_NAME,
                files=[
                    (full_first_file_name, FIRST_FILE_CONTENTS),
                    (full_second_file_name, SECOND_FILE_CONTENTS)
                ]
            )
            self.enforcements_page.click_save_button()
            self.enforcements_page.wait_for_table_to_load()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_load()
            self.devices_page.enforce_action_on_query(
                self.devices_page.FILTER_HOSTNAME.format(filter_value=WMI_QUERIES_DEVICE),
                RUN_CMD_ENFORCEMENT_NAME
            )
            self.enforcements_page.switch_to_page()
            self.devices_page.wait_for_table_to_load()
            self.enforcements_page.click_tasks_button()
            self.enforcements_page.wait_for_table_to_load()
            self.enforcements_page.click_row()

            def _check_task_finished():
                self.driver.refresh()
                time.sleep(3)
                try:
                    assert self.enforcements_page.find_task_action_success(RUN_CMD_ACTION_NAME).text == str(1)
                    return True
                except Exception:
                    return False

            wait_until(_check_task_finished, check_return_value=True, total_timeout=60 * 3, interval=5)
            self.enforcements_page.find_task_action_success(RUN_CMD_ACTION_NAME).click()
            self.devices_page.wait_for_table_to_load()
            assert self.devices_page.count_entities() == 1
            self.devices_page.click_row()
            self.devices_page.wait_for_spinner_to_end()
            self.devices_page.click_enforcement_tasks_tab()
            self.devices_page.click_tab(f'{RUN_CMD_ENFORCEMENT_NAME} - Task 1')
            table_data = self.devices_page.get_field_table_data()
            assert len(table_data) == 1
            enforcement_set_name, action_name, is_success, output = table_data[0]
            assert enforcement_set_name == RUN_CMD_ACTION_NAME
            assert action_name == Action.run_windows_shell_command.value
            assert is_success == ''
            assert 'axonius_output_' in output
            self.devices_page.click_extended_data_tasks_tab()
            vertical_tabs = self.devices_page.find_vertical_tabs()
            assert [f'Action \'{RUN_CMD_ACTION_NAME}\''] == vertical_tabs, 'Different vertical tabs than excepted'
            custom_execution_data = self.devices_page.get_all_custom_data()
            assert len(custom_execution_data) == 1
            assert 'Action type: shell. Command:' in custom_execution_data[0]

            # Check file existence
            dir_contents, after_dir = custom_execution_data[0].split(
                f'\n{self.enforcements_page.FIRST_ENFORCEMENT_EXECUTION_DIR_SEPERATOR}')
            assert full_first_file_name in dir_contents  # the file has to be there
            assert full_second_file_name in dir_contents  # the file has to be there
            before_dir, dir_contents = custom_execution_data[0].split(
                f'\n{self.enforcements_page.SECOND_ENFORCEMENT_EXECUTION_DIR_SEPERATOR}')
            assert full_first_file_name not in dir_contents  # the file was deleted, shouldn't be there
            assert full_second_file_name not in dir_contents  # the file was deleted, shouldn't be there

            # Check file contents
            assert FIRST_FILE_CONTENTS in custom_execution_data[0]
            assert SECOND_FILE_CONTENTS in custom_execution_data[0]
