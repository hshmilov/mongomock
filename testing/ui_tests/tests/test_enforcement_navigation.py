from ui_tests.tests.ui_consts import WINDOWS_QUERY_NAME
from ui_tests.tests.ui_test_base import TestBase

ENFORCEMENT_NAME_INCLUDE = 'Test Enforcement Include'
ENFORCEMENT_NAME_EXCLUDE = 'Test Enforcement Exclude'
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
        self.enforcements_page.fill_enter_table_search(WINDOWS_QUERY_NAME)
        self.enforcements_page.wait_for_table_to_load()

        tasks = self.enforcements_page.get_tasks_data_from_table()

        for task in tasks:
            assert task.name == ENFORCEMENT_NAME_INCLUDE

    def test_enforcement_long_running_task_status(self):
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()

        # Add new enforcement (1)
        self.enforcements_page.create_notifying_enforcement(enforcement_name='long_running',
                                                            enforcement_view='Devices')
        self.enforcements_page.edit_enforcement('long_running')
        self.enforcements_page.click_run_button()
        self.enforcements_page.wait_for_toaster_to_end(TOASTER_TEXT)

        self.adapters_page.wait_for_element_present_by_text(self.enforcements_page.SAVE_AND_RUN_BUTTON_TEXT)
        self.notification_page.wait_for_count(1)
        self.enforcements_page.click_tasks_button()
        self.enforcements_page.wait_for_table_to_load()

        assert self.enforcements_page.get_task_status(1) == 'Completed'

        # mock long running task by changing directly the values in the db
        self.axonius_system.get_tasks_db().update_one({
            'post_json.report_name': 'long_running'
        }, {
            '$set': {
                'job_completed_state': 'Running'
            }
        })
        #
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.edit_enforcement('long_running')
        self.enforcements_page.click_tasks_button()
        # test if gui show 'in progress' task
        assert self.enforcements_page.get_task_status(1) == 'In Progress'
        # delete the mutated task from the db
        self.axonius_system.get_tasks_db().delete_one({'post_json.report_name': 'long_running'})
