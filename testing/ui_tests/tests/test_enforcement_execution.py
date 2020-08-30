# pylint: disable=too-many-statements
import time
import pytest

from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
from axonius.utils.wait import wait_until
from services.adapters.wmi_service import WmiService
from test_credentials.test_ad_credentials import WMI_QUERIES_DEVICE
from ui_tests.pages.enforcements_page import Action
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import MANAGED_DEVICES_QUERY_NAME

RUN_CMD_ACTION_NAME = 'Run Windows Command'

# Files which are uploaded remotely must be named 'axonius_' because we have a mechanism that deletes them
# after a day in case they were not deleted automatically.
CONSTANT_PREFIX = 'axonius_'
FIRST_FILE_NAME = 'first_file_name'
SECOND_FILE_NAME = 'second_file_name'
FIRST_FILE_CONTENTS = 'first-file-contents'
SECOND_FILE_CONTENTS = 'second-file-contents'
SUCCESS_ACTION_NAME = 'Random Success Action'


class TestEnforcementExecution(TestBase):
    def test_enforcement_flow(self):
        """
        Testing enforcement execution flow
        1 - Check the initial state of the enforcement creation page:
            The successive actions, trigger and run buttons should be disabled.
            View tasks button should navigate us to the generic tasks page.
        2 - Fill enforcement name and create tagging action without saving,
            Click cancel and make sure we see the action library again
        3 - Create tagging enforcement and check that now all the successive buttons are enabled
        4 - Create trigger and check that run button is enabled
        5 - Create first success action and verify that its name cannot be used for the second one.
            Then delete the first one and verify that we can use the deleted action name on the second one.
            (This checks for both the deletion and action name validation logic)
            Also, check edit mode behavior
        6 - Check deletion and recreation behavior for trigger
        7 - Check deletion and recreation behavior for main action
        """
        # Check 1
        self._check_initial_state()

        # Check 2
        self._check_cancel_resets_input()

        # Check 3
        self._check_defined_state()

        # Check 4
        self._check_trigger_creation()

        # Check 5
        self._check_successive_action_flow()

        # Check 6
        self._check_trigger_recreation()

        # Check 7
        self._check_main_action_recreation()

    def _check_main_action_recreation(self):
        self.enforcements_page.click_action_by_name(self.enforcements_page.SPECIAL_TAG_ACTION)
        self._assert_edit_button_behavior()
        self._assert_main_action_deletion()
        with pytest.raises(NoSuchElementException):
            self.enforcements_page.click_action_by_name(self.enforcements_page.SPECIAL_TAG_ACTION)
        self.enforcements_page.select_trigger()
        assert not self.enforcements_page.is_run_button_disabled()
        self.enforcements_page.click_action_by_name(self.enforcements_page.SPECIAL_TAG_ACTION)
        self._assert_main_action_deletion()
        self.enforcements_page.click_action_by_name(SUCCESS_ACTION_NAME)
        assert not self.enforcements_page.is_run_button_disabled()
        self.enforcements_page.click_action_by_name(self.enforcements_page.SPECIAL_TAG_ACTION)
        self._assert_main_action_deletion()
        self.enforcements_page.add_tag_entities()
        self.enforcements_page.assert_config_panel_in_display_mode()
        assert not self.enforcements_page.is_run_button_disabled()

    def _check_trigger_recreation(self):
        self.enforcements_page.select_trigger()
        self._assert_edit_button_behavior()
        self.enforcements_page.click_delete_button()
        self.enforcements_page.safeguard_click_confirm(self.enforcements_page.DELETE_BUTTON_TEXT)
        self.enforcements_page.wait_for_element_present_by_css(self.enforcements_page.TRIGGER_CONF_CONTAINER_CSS)
        self.enforcements_page.assert_config_panel_in_edit_mode()
        assert self.enforcements_page.is_run_button_disabled()
        self.enforcements_page.create_trigger(MANAGED_DEVICES_QUERY_NAME)
        self.enforcements_page.assert_config_panel_in_display_mode()
        assert not self.enforcements_page.is_run_button_disabled()

    def _check_successive_action_flow(self):
        self.enforcements_page.page_back()
        self.enforcements_page.add_tag_entities(name=SUCCESS_ACTION_NAME,
                                                action_cond=self.enforcements_page.SUCCESS_ACTIONS_TEXT)
        with pytest.raises(ElementNotInteractableException):
            self.enforcements_page.add_tag_entities(name=SUCCESS_ACTION_NAME,
                                                    action_cond=self.enforcements_page.SUCCESS_ACTIONS_TEXT)
        self.enforcements_page.click_action_by_name(SUCCESS_ACTION_NAME)
        self._assert_edit_button_behavior()
        self.enforcements_page.click_delete_button()
        self.enforcements_page.safeguard_click_confirm(self.enforcements_page.DELETE_BUTTON_TEXT)
        self.enforcements_page.wait_for_action_library()
        with pytest.raises(NoSuchElementException):
            self.enforcements_page.click_action_by_name(SUCCESS_ACTION_NAME)
        self.enforcements_page.add_tag_entities(name=SUCCESS_ACTION_NAME,
                                                action_cond=self.enforcements_page.SUCCESS_ACTIONS_TEXT)

    def _check_trigger_creation(self):
        self.enforcements_page.create_trigger(MANAGED_DEVICES_QUERY_NAME)
        assert not self.enforcements_page.is_run_button_disabled()
        self.enforcements_page.get_view_tasks_button().click()
        self.enforcements_page.wait_for_table_to_be_responsive()
        assert self.enforcements_page.get_enforcement_name_of_view_tasks() == \
            self.enforcements_page.DUMMY_ENFORCEMENT_NAME

    def _check_defined_state(self):
        self.enforcements_page.fill_enforcement_name(self.enforcements_page.DUMMY_ENFORCEMENT_NAME)
        self.enforcements_page.add_tag_entities()
        assert self._is_successive_actions_and_trigger_clickable()
        assert self.enforcements_page.is_run_button_disabled()

    def _check_cancel_resets_input(self):
        self.enforcements_page.page_back()
        self.enforcements_page.add_tag_entities(save=False)
        self.enforcements_page.get_cancel_button().click()
        self.enforcements_page.wait_for_action_library()
        assert self.devices_page.get_enforcement_name() == ''

    def _check_initial_state(self):
        self.enforcements_page.create_basic_empty_enforcement(self.enforcements_page.DUMMY_ENFORCEMENT_NAME)
        assert not self._is_successive_actions_and_trigger_clickable()
        assert self.enforcements_page.is_run_button_disabled()
        self.enforcements_page.get_view_tasks_button().click()
        self.enforcements_page.wait_for_table_to_be_responsive()
        with pytest.raises(NoSuchElementException):
            self.enforcements_page.get_enforcement_name_of_view_tasks()

    def _assert_main_action_deletion(self):
        self.enforcements_page.click_delete_button()
        self.enforcements_page.safeguard_click_confirm(self.enforcements_page.DELETE_BUTTON_TEXT)
        self.enforcements_page.wait_for_action_library()
        self.enforcements_page.assert_config_panel_in_edit_mode()
        assert self.enforcements_page.is_run_button_disabled()

    def _assert_edit_button_behavior(self):
        self.enforcements_page.assert_config_panel_in_display_mode()
        self.enforcements_page.click_edit_button()
        self.enforcements_page.assert_config_panel_in_edit_mode()
        assert self.enforcements_page.is_run_button_disabled()
        self.enforcements_page.get_cancel_button().click()
        self.enforcements_page.assert_config_panel_in_display_mode()
        assert not self.enforcements_page.is_run_button_disabled()

    def _is_successive_actions_and_trigger_clickable(self):
        return (self.enforcements_page.is_element_clickable(self.enforcements_page.get_success_actions_button())
                and self.enforcements_page.is_element_clickable(self.enforcements_page.get_failure_actions_button())
                and self.enforcements_page.is_element_clickable(self.enforcements_page.get_post_actions_button())
                and self.enforcements_page.is_element_clickable(self.enforcements_page.get_trigger_button()))

    def test_run_cmd_with_files(self):
        with WmiService().contextmanager(take_ownership=True):
            self.base_page.run_discovery()
            self.enforcements_page.create_basic_empty_enforcement(self.enforcements_page.RUN_CMD_ENFORCEMENT_NAME)
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
            self.enforcements_page.switch_to_page()
            self.enforcements_page.wait_for_table_to_be_responsive()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()
            self.devices_page.enforce_action_on_query(
                self.devices_page.FILTER_HOSTNAME.format(filter_value=WMI_QUERIES_DEVICE),
                self.enforcements_page.RUN_CMD_ENFORCEMENT_NAME
            )
            self.enforcements_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()
            self.enforcements_page.click_tasks_button()
            self.enforcements_page.wait_for_table_to_be_responsive()
            self.enforcements_page.click_row()

            def _check_task_finished():
                self.driver.refresh()
                time.sleep(3)
                try:
                    assert self.enforcements_page.find_task_action_success(RUN_CMD_ACTION_NAME).text == str(1)
                    return True
                except Exception:
                    return False

            wait_until(_check_task_finished, check_return_value=True, total_timeout=60 * 5, interval=5)
            self.enforcements_page.find_task_action_success(RUN_CMD_ACTION_NAME).click()
            self.devices_page.wait_for_table_to_load()
            assert self.devices_page.count_entities() == 1
            self.devices_page.click_row()
            self.devices_page.click_enforcement_tasks_tab()
            table_data = self.devices_page.get_field_table_data_with_ids()
            assert len(table_data) == 1
            enforcement_set_id, enforcement_set_name, action_name, is_success, output = table_data[0]
            assert enforcement_set_id == f'{self.enforcements_page.RUN_CMD_ENFORCEMENT_NAME} - Task 1'
            assert enforcement_set_name == RUN_CMD_ACTION_NAME
            assert action_name == Action.run_windows_shell_command.value
            assert is_success == 'Yes'
            assert 'success' in output
            self.devices_page.click_extended_data_tasks_tab()
            vertical_tabs = self.devices_page.find_vertical_tabs()
            assert any(RUN_CMD_ACTION_NAME.lower().replace(' ', '_') in name for name in vertical_tabs), \
                'Different vertical tabs than excepted'
            custom_execution_data = self.devices_page.get_all_custom_data()
            assert len(custom_execution_data) == 4

            # Check file existence
            command_output = custom_execution_data[1]
            dir_contents, after_dir = command_output.split(
                f'\n{self.enforcements_page.FIRST_ENFORCEMENT_EXECUTION_DIR_SEPERATOR}')
            assert full_first_file_name in dir_contents  # the file has to be there
            assert full_second_file_name in dir_contents  # the file has to be there
            before_dir, dir_contents = command_output.split(
                f'\n{self.enforcements_page.SECOND_ENFORCEMENT_EXECUTION_DIR_SEPERATOR}')
            assert full_first_file_name not in dir_contents  # the file was deleted, shouldn't be there
            assert full_second_file_name not in dir_contents  # the file was deleted, shouldn't be there

            # Check file contents
            assert FIRST_FILE_CONTENTS in command_output
            assert SECOND_FILE_CONTENTS in command_output
