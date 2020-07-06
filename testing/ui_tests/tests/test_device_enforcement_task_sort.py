from axonius.utils.wait import wait_until
from ui_tests.tests.device_test_base import TestDeviceBase
from ui_tests.tests.ui_consts import WINDOWS_QUERY_NAME


class TestDeviceEnforcementTaskSort(TestDeviceBase):
    def test_device_enforcement_task_sort(self):
        """
        Test for checking the sort order in the enforcement tasks of a device
        Actions:
            - Running discovery and finding some Windows devices (through AD adapter)
            - Creating a saved query for finding Windows devices
              * This saved query will be used in both enforcement sets as described below
            - Creating 'first enforcement set' to add tag and running it twice (for Windows devices)
            - Creating 'second enforcement set' to add tag and running it once (for Windows devices)
            - In the enforcement tasks table of a certain windows device, check that the tasks are sorted
            - The sort is according to the enforcement set id in a DESCENDING order
        """
        print('starting test_device_enforcement_task_sort', flush=True)
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, WINDOWS_QUERY_NAME)
        self.enforcements_page.create_tag_enforcement(self.RUN_TAG_ENFORCEMENT_NAME, WINDOWS_QUERY_NAME,
                                                      'tag search test', 'tag search test', 2)
        self.enforcements_page.create_tag_enforcement(self.RUN_TAG_ENFORCEMENT_NAME_SECOND, WINDOWS_QUERY_NAME,
                                                      'second tag search test', 'second tag search test', 1)

        # check in enforcements tasks that all running enforcements were completed
        wait_until(lambda: self.assert_completed_tasks(expected_completed_count=3), total_timeout=60 * 5)

        self.devices_page.switch_to_page()
        self.devices_page.execute_saved_query(WINDOWS_QUERY_NAME)
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row()
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.click_enforcement_tasks_tab()
        table_info = self.devices_page.get_field_table_data_with_ids()
        assert len(table_info) == 3
        enforcement_set_id = table_info[0][0]
        assert enforcement_set_id[enforcement_set_id.find('Task'):] == 'Task 3'
        enforcement_set_id = table_info[1][0]
        assert enforcement_set_id[enforcement_set_id.find('Task'):] == 'Task 2'
        enforcement_set_id = table_info[2][0]
        assert enforcement_set_id[enforcement_set_id.find('Task'):] == 'Task 1'

    def assert_completed_tasks(self, expected_completed_count):
        self.enforcements_page.switch_to_page()
        self.enforcements_page.click_tasks_button()
        self.enforcements_page.wait_for_table_to_load()

        count = len(self.enforcements_page.find_elements_by_xpath(self.enforcements_page.COMPLETED_CELL_XPATH))
        return count == expected_completed_count
