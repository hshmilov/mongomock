from axonius.utils.wait import wait_until
from ui_tests.tests.ui_test_base import TestBase


class TestEnforcementPanel(TestBase):
    FIRST_ENFORCEMENT_NAME = 'First Enforcement Name'
    FIRST_ACTION_NAME = 'First Action Name'
    FIRST_TAG = 'First Tag'
    SECOND_ENFORCEMENT_NAME = 'Second Enforcement Name'
    SECOND_ACTION_NAME = 'Second Action Name'
    SECOND_TAG = 'Second Tag'
    DUMMY_ENFORCEMENT_NAME = 'Dummy Enforcement'
    DUMMY_ACTION_NAME = 'Dummy Action'
    DUMMY_TAG = 'Dummy Tag'
    SUCCESS_MESSAGE = 'Enforcement task has been created successfully'
    ENFORCEMENT_NAME_REQUIRED_ERROR = 'Enforcement Name is a required field'
    ENFORCEMENT_NAME_TAKEN_ERROR = 'Name already taken by another Enforcement'
    ACTION_NAME_REQUIRED_ERROR = 'Action name is a required field'
    ACTION_NAME_TAKEN_ERROR = 'Name already taken by another saved Action'
    ACTION_NOT_CONFIGURED_ERROR = 'Action must be correctly configured for the Enforcement'

    def test_enforcement_panel(self):
        """
        Testing enforcement panel operations for devices
        1 - Create and run an enforcement from the panel and check that it ran successfully.
        2 - Run the above created enforcement on a different device and check navigation to the EC tasks.
        3 - Open the enforcement panel and verify that all data is cleared.
            Fill action data and go back, open action data again and see that data is cleared.
        4 - Create and run a second enforcement from the panel and check that it ran successfully.
        5 - Check enforcement panel validations
        """
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()

        # Check 1:
        self._test_create_and_run_enforcement(self.FIRST_ENFORCEMENT_NAME, self.FIRST_ACTION_NAME, self.FIRST_TAG, 0)

        # Check 2:
        self._test_new_task_navigation(self.FIRST_ENFORCEMENT_NAME)

        # Check 3:
        self._test_enforcement_panel_cleared()

        # Check 4:
        self._test_create_and_run_enforcement(self.SECOND_ENFORCEMENT_NAME, self.SECOND_ACTION_NAME, self.SECOND_TAG, 2)

        # Check 5:
        self._test_enforcement_panel_validations()

    def _test_create_and_run_enforcement(self, enforcement_name, action_name, tag, row_number):
        self.devices_page.click_row_checkbox(row_number + 1)
        self.devices_page.create_and_run_tag_enforcement(enforcement_name, action_name, tag)
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.get_column_data_slicer(self.devices_page.FIELD_TAGS)[row_number] == tag

    def _test_new_task_navigation(self, enforcement_name):
        self.devices_page.click_row_checkbox(2)
        self.devices_page.run_enforcement_on_selected_device(enforcement_name, False)
        assert self.devices_page.get_enforcement_result_link().text == self.SUCCESS_MESSAGE
        self.devices_page.get_enforcement_result_link().click()
        self.enforcements_page.wait_for_table_to_be_responsive()
        self.enforcements_page.wait_for_element_present_by_text(self.FIRST_ENFORCEMENT_NAME)
        wait_until(lambda: self.enforcements_page.count_entities() == 2)
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()

    def _test_enforcement_panel_cleared(self):
        self.devices_page.click_row_checkbox()
        self.devices_page.open_enforcement_panel()
        assert self.devices_page.get_enforcement_name() == ''
        self.devices_page.open_action_tag_config()
        self.devices_page.fill_enforcement_action_name(self.DUMMY_ACTION_NAME)
        self.devices_page.go_back_to_action_library()
        self.devices_page.open_action_tag_config()
        assert self.driver.find_element_by_id(self.devices_page.ACTION_NAME_ID).text == ''
        self.devices_page.close_side_panel()
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.click_row_checkbox()

    def _test_enforcement_panel_validations(self):
        self.devices_page.click_row_checkbox()
        self.devices_page.open_enforcement_panel()
        self._assert_error_message('')
        self.devices_page.key_down_tab()
        self._assert_error_message(self.ENFORCEMENT_NAME_REQUIRED_ERROR)
        self.devices_page.fill_enforcement_name(self.FIRST_ENFORCEMENT_NAME)
        self._assert_error_message(self.ENFORCEMENT_NAME_TAKEN_ERROR)
        self.devices_page.fill_enforcement_name(self.DUMMY_ENFORCEMENT_NAME)
        self._assert_error_message('')
        self.devices_page.open_action_tag_config()
        self._assert_error_message('')
        self.devices_page.key_down_tab()
        self._assert_error_message(self.ACTION_NAME_REQUIRED_ERROR)
        self.devices_page.fill_enforcement_action_name(self.FIRST_ACTION_NAME)
        self._assert_error_message(self.ACTION_NAME_TAKEN_ERROR)
        self.devices_page.fill_enforcement_action_name(self.DUMMY_ACTION_NAME)
        self._assert_error_message(self.ACTION_NOT_CONFIGURED_ERROR)
        self.devices_page.select_option(
            self.devices_page.DROPDOWN_TAGS_CSS,
            self.devices_page.DROPDOWN_TEXT_BOX_CSS, self.devices_page.DROPDOWN_NEW_OPTION_CSS, self.DUMMY_TAG
        )
        assert self.devices_page.get_enforcement_panel_error() == ''
        assert not self.devices_page.is_enforcement_panel_save_button_disabled()

    def _assert_error_message(self, error_message):
        assert self.devices_page.is_enforcement_panel_save_button_disabled()
        assert self.devices_page.get_enforcement_panel_error() == error_message
