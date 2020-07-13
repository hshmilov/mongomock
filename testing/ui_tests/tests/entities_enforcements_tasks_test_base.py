import time

from ui_tests.tests.permissions_test_base import PermissionsTestBase


class EntitiesEnforcementTasksTestBase(PermissionsTestBase):

    def create_tag_enforcement_run_it_return_entity_count(self):
        custom_unmanaged_devices = 'custom unmanaged devices'
        self.devices_page.create_saved_query(self.devices_page.UNMANAGED_QUERY, custom_unmanaged_devices)
        self.enforcements_page.switch_to_page()
        self.enforcements_page.create_tag_enforcement(self.enforcements_page.RUN_TAG_ENFORCEMENT_NAME,
                                                      custom_unmanaged_devices,
                                                      'tag search test', 'tag search test')
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.execute_saved_query(custom_unmanaged_devices)
        self.devices_page.wait_for_table_to_be_responsive()
        entity_count = self.devices_page.get_table_count()
        self.enforcements_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()
        self.enforcements_page.click_tasks_button()
        self.enforcements_page.wait_for_table_to_be_responsive()
        # wait for some rendering and animation that cause StaleElementReferenceException
        time.sleep(3)
        self.enforcements_page.wait_until_enforcement_task_completion()
        return entity_count

    def assert_device_enforcement_task(self, enforcement_set_id):
        assert enforcement_set_id == f'{self.enforcements_page.RUN_TAG_ENFORCEMENT_NAME} - Task 1'
        self.devices_page.search_enforcement_tasks_search_input(enforcement_set_id)
        assert self.devices_page.get_enforcement_tasks_count() == 1
        self.devices_page.search_enforcement_tasks_search_input(enforcement_set_id + '1')
        assert self.devices_page.get_enforcement_tasks_count() == 0
        self.devices_page.search_enforcement_tasks_search_input('')
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.click_task_name(enforcement_set_id)
        self.enforcements_page.wait_for_action_result()
        assert self.enforcements_page.get_task_name() == enforcement_set_id
