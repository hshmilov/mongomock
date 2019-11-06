import time

from axonius.utils.wait import wait_until
from ui_tests.tests.ui_test_base import TestBase

AZURE_AD_ADAPTER_NAME = 'Microsoft Active Directory (AD)'


class TestDevice(TestBase):
    """
    Device page (i.e view on a single device) related tests
    """
    RUN_TAG_ENFORCEMENT_NAME = 'Run Tag Enforcement'

    def test_add_predefined_fields_on_device(self):
        """
        Tests that we can more than one predefined fields on a device
        Actions:
            - Go to device page
            - Select a device
            - Got to custom data tab
            - Press edit fields
            - Add predefined field & Save
                - Verify field was added
            - Create another predefined field & Save
                - Verify new data also exists
        """
        # === Step 1 === #
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        # === Step 2 === #
        self.devices_page.switch_to_page()
        self.devices_page.click_row()
        self.devices_page.click_custom_data_tab()
        self.devices_page.click_custom_data_edit()
        self.devices_page.click_custom_data_add_predefined()
        parent = self.devices_page.find_custom_fields_items()[-1]
        self.devices_page.select_custom_data_field(self.devices_page.FIELD_ASSET_NAME, parent=parent)
        self.devices_page.fill_custom_data_value('DeanSysman', parent=parent, input_type_string=True)
        self.devices_page.save_custom_data()
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.find_element_by_text(self.devices_page.FIELD_ASSET_NAME) is not None
        assert self.devices_page.find_element_by_text('DeanSysman') is not None
        self.devices_page.click_custom_data_edit()
        self.devices_page.click_custom_data_add_predefined()
        parent = self.devices_page.find_custom_fields_items()[-1]
        self.devices_page.select_custom_data_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=parent)
        self.devices_page.fill_custom_data_value('DeanSysman2', parent=parent, input_type_string=True)
        self.devices_page.save_custom_data()
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.find_element_by_text(self.devices_page.FIELD_ASSET_NAME) is not None
        assert self.devices_page.find_element_by_text('DeanSysman2') is not None

    def test_device_enforcement_tasks_search(self):
        self.enforcements_page.switch_to_page()
        self.base_page.run_discovery()
        self.enforcements_page.create_tag_enforcement(self.RUN_TAG_ENFORCEMENT_NAME,
                                                      self.devices_page.VALUE_SAVED_QUERY_WINDOWS,
                                                      'tag search test',
                                                      'tag search test')
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.execute_saved_query(self.devices_page.VALUE_SAVED_QUERY_WINDOWS)
        self.devices_page.wait_for_table_to_load()
        entity_count = self.devices_page.get_table_count()

        self.enforcements_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.enforcements_page.click_tasks_button()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_row()

        def _check_task_finished():
            self.driver.refresh()
            time.sleep(3)
            try:
                assert self.enforcements_page.find_task_action_success(self.RUN_TAG_ENFORCEMENT_NAME).text \
                    == str(entity_count)
                return True
            except Exception:
                return False

        wait_until(_check_task_finished, check_return_value=True, total_timeout=60 * 3, interval=5)
        self.enforcements_page.find_task_action_success(self.RUN_TAG_ENFORCEMENT_NAME).click()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == entity_count
        self.devices_page.click_row()
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.click_enforcement_tasks_tab()
        table_data = self.devices_page.get_field_table_data_with_ids()
        assert len(table_data) == 1
        enforcement_set_id, enforcement_set_name, action_name, is_success, output = table_data[0]
        assert enforcement_set_id == f'{self.RUN_TAG_ENFORCEMENT_NAME} - Task 1'
        self.enforcements_page.search_enforcement_tasks_search_input(enforcement_set_id)
        assert self.enforcements_page.get_enforcement_tasks_count() == 1
        self.enforcements_page.search_enforcement_tasks_search_input(enforcement_set_id + '1')
        assert self.enforcements_page.get_enforcement_tasks_count() == 0
