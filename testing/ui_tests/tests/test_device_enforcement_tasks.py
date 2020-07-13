from ui_tests.tests.entities_enforcements_tasks_test_base import EntitiesEnforcementTasksTestBase
from ui_tests.tests.ui_consts import (WINDOWS_QUERY_NAME)


class TestDeviceEnforcementTasks(EntitiesEnforcementTasksTestBase):
    """
    Device Enforcement Tasks page (i.e view on a single device) related tests
    """

    def test_device_enforcement_tasks(self):
        print('starting test_device_enforcement_tasks', flush=True)

        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, WINDOWS_QUERY_NAME)
        self.enforcements_page.switch_to_page()
        self.base_page.run_discovery()
        entity_count = self.create_tag_enforcement_run_it_return_entity_count()
        self.enforcements_page.find_task_action_success(self.enforcements_page.RUN_TAG_ENFORCEMENT_NAME).click()
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.count_entities() == entity_count
        self.devices_page.click_row()
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.click_enforcement_tasks_tab()
        table_data = self.devices_page.get_field_table_data_with_ids()
        assert len(table_data) == 1
        enforcement_set_id, enforcement_set_name, action_name, is_success, output = table_data[0]
        self.assert_device_enforcement_task(enforcement_set_id)
        self.logger.info('finished test_device_enforcement_tasks')

    def test_device_task_export_csv(self):
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, WINDOWS_QUERY_NAME)
        self.enforcements_page.switch_to_page()
        self.base_page.run_discovery()
        self.create_tag_enforcement_run_it_return_entity_count()
        self.enforcements_page.find_task_action_success(self.enforcements_page.RUN_TAG_ENFORCEMENT_NAME).click()
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.click_row()
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.click_enforcement_tasks_tab()
        self.devices_page.click_device_enforcement_task_export_csv()
        file_content = self.get_downloaded_file_content('enforcement_tasks', '.csv')
        assert file_content
        self.devices_page.assert_csv_match_ui_data_with_content(file_content, exclude_column_indexes=[1])
