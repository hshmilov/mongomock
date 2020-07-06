import os
import time

from axonius.utils.wait import wait_until
from ui_tests.tests.device_test_base import TestDeviceBase
from ui_tests.tests.ui_consts import WINDOWS_QUERY_NAME


class TestDeviceEnforcementTasks(TestDeviceBase):
    def test_device_enforcement_tasks(self):
        print('starting test_device_enforcement_tasks', flush=True)

        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, WINDOWS_QUERY_NAME)
        self.enforcements_page.switch_to_page()
        self.base_page.run_discovery()
        self.enforcements_page.create_tag_enforcement(
            self.RUN_TAG_ENFORCEMENT_NAME, WINDOWS_QUERY_NAME, 'tag search test', 'tag search test')
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.execute_saved_query(WINDOWS_QUERY_NAME)
        self.devices_page.wait_for_table_to_load()
        entity_count = self.devices_page.get_table_count()

        self.enforcements_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.enforcements_page.click_tasks_button()
        self.enforcements_page.wait_for_table_to_load()
        # wait for some rendering and animation that cause StaleElementReferenceException
        time.sleep(3)
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

        self.logger.info('waiting for check_task_finished')
        wait_until(_check_task_finished, check_return_value=True, total_timeout=60 * 3, interval=5)
        self.logger.info('done waiting for check_task_finished')
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
        self.devices_page.search_enforcement_tasks_search_input(enforcement_set_id)
        assert self.devices_page.get_enforcement_tasks_count() == 1
        self.devices_page.search_enforcement_tasks_search_input(enforcement_set_id + '1')
        assert self.devices_page.get_enforcement_tasks_count() == 0
        self.devices_page.search_enforcement_tasks_search_input('')
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_task_name(enforcement_set_id)
        self.enforcements_page.wait_for_action_result()
        assert self.enforcements_page.get_task_name() == enforcement_set_id
        self._test_task_export_csv()
        self.logger.info('finished test_device_enforcement_tasks')

    def _test_task_export_csv(self):
        self.enforcements_page.find_task_action_success(self.RUN_TAG_ENFORCEMENT_NAME).click()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row()
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.click_enforcement_tasks_tab()
        self.devices_page.click_button('Export CSV')
        time.sleep(7)
        for root, dirs, files in os.walk(self.ui_tests_download_dir):
            for file in files:
                if file.endswith('.csv') and file.find('enforcement_tasks') != -1:
                    f = open(f'{self.ui_tests_download_dir}/{file}', 'rb')
                    #  perform calculation
                    self.devices_page.assert_csv_match_ui_data_with_content(f.read())
                    f.close()
