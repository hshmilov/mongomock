from ui_tests.tests.ui_test_base import TestBase

ENFORCEMENT_NAME_INCLUDE = 'Test Enforcement Include'
ENFORCEMENT_NAME_EXCLUDE = 'Test Enforcement Exclude'
SAVED_QUERY_SELECTION = 'Windows Operating System'
TOASTER_TEXT = 'Enforcement Task is in progress'
DEFAULT_ACTION_NAME = 'Special Push Notification'
ANOTHER_ACTION_NAME = 'Another Special Push Notification'


class TestEnforcementNavigation(TestBase):
    def test_new(self):

        # Go to enforcements page
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()

        # Add new enforcements (2)
        self.enforcements_page.create_notifying_enforcement(enforcement_name=ENFORCEMENT_NAME_INCLUDE,
                                                            enforcement_view='Devices')
        self.enforcements_page.create_notifying_enforcement(enforcement_name=ENFORCEMENT_NAME_EXCLUDE,
                                                            enforcement_view='Devices')
        self.enforcements_page.edit_enforcement(ENFORCEMENT_NAME_INCLUDE)

        # Run enforcement & wait to end

        self.enforcements_page.click_run_button()
        self.enforcements_page.wait_for_toaster_to_end(TOASTER_TEXT)

        self.adapters_page.wait_for_element_present_by_text(self.enforcements_page.SAVE_AND_RUN_BUTTON_TEXT)
        self.enforcements_page.click_tasks_button()
        self.enforcements_page.wait_for_table_to_load()

        # Search and filter tasks
        self.enforcements_page.fill_enter_table_search(SAVED_QUERY_SELECTION)
        self.enforcements_page.wait_for_table_to_load()

        tasks = self.enforcements_page.get_tasks_data_from_table()

        for task in tasks:
            assert task.name == ENFORCEMENT_NAME_INCLUDE
