import time
from datetime import datetime
from datetime import timedelta

import pytest

from test_helpers.file_mock_credentials import FileForCredentialsMock

from ui_tests.tests.ui_consts import WINDOWS_QUERY_NAME, CSV_NAME, CSV_PLUGIN_NAME
from ui_tests.tests.ui_test_base import TestBase

from testing.test_credentials.test_csv_credentials import CSV_FIELDS
from axonius.utils.wait import wait_until
from services.adapters.csv_service import CsvService
AZURE_AD_ADAPTER_NAME = 'Microsoft Active Directory (AD)'


class TestDevice(TestBase):
    """
    Device page (i.e view on a single device) related tests
    """
    RUN_TAG_ENFORCEMENT_NAME = 'Run Tag Enforcement'
    RUN_TAG_ENFORCEMENT_NAME_SECOND = 'Second Run Tag Enforcement'

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
        print('starting test_add_predefined_fields_on_device', flush=True)
        # === Step 1 === #
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        # === Step 2 === #
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
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

        self.logger.info('finished test_device_enforcement_tasks')

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

    def test_add_predefined_fields_updates_general(self):
        print('starting test_add_predefined_fields_updates_general', flush=True)
        asset_name = 'asset name 123'
        host_name = 'host name 123'
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row()
        self.devices_page.click_custom_data_tab()
        self.devices_page.click_custom_data_edit()

        self.devices_page.click_custom_data_add_predefined()
        parent = self.devices_page.find_custom_fields_items()[-1]
        self.devices_page.select_custom_data_field(self.devices_page.FIELD_ASSET_NAME, parent=parent)
        self.devices_page.fill_custom_data_value(asset_name, parent=parent, input_type_string=True)

        self.devices_page.click_custom_data_add_predefined()
        parent = self.devices_page.find_custom_fields_items()[-1]
        self.devices_page.select_custom_data_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=parent)
        self.devices_page.fill_custom_data_value(host_name, parent=parent, input_type_string=True)

        self.devices_page.save_custom_data()
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.safe_refresh()
        self.devices_page.click_general_tab()
        assert self.devices_page.find_element_by_text(self.devices_page.FIELD_ASSET_NAME)
        assert self.devices_page.find_element_by_text(asset_name)

        assert self.devices_page.find_element_by_text(self.devices_page.FIELD_HOSTNAME_TITLE)
        assert self.devices_page.find_element_by_text(host_name)

    def test_last_seen_expanded_cell_sort(self):
        """
        Test that the expanded details table under last seen field is sorted decreasingly by date-time
        Actions:
            - Go to device page
            - Run discovery
            - Press the expand data button of the first row
            - Make sure that the details table is sorted decreasingly by last seen field
        """
        print('starting test_last_seen_expanded_cell_sort', flush=True)
        with CsvService().contextmanager(take_ownership=True):
            first_date = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
            second_date = (datetime.today() - timedelta(days=2)).strftime('%Y-%m-%d')
            third_date = (datetime.today() - timedelta(days=3)).strftime('%Y-%m-%d')

            client_details = {
                'user_id': 'user',
                # an array of char
                self.adapters_page.CSV_FILE_NAME: FileForCredentialsMock(
                    'csv_name',
                    ','.join(CSV_FIELDS) +
                    f'\nJohn,Serial1,Windows,11:22:22:33:11:33,Office,{second_date} 02:11:24.485Z, 127.0.0.2'
                    f'\nJohn,Serial2,Windows,11:22:22:33:11:33,Office,{second_date} 02:17:24.485Z, 127.0.0.2'
                    f'\nJohn,Serial3,Windows,11:22:22:33:11:33,Office,{first_date} 05:17:24.485Z, 127.0.0.2'
                    f'\nJohn,Serial4,Windows,11:22:22:33:11:33,Office,{first_date} 06:17:24.485Z, 127.0.0.2'
                    f'\nJohn,Serial5,Windows,11:22:22:33:11:33,Office,{third_date} 02:15:24.485Z, 127.0.0.2')
            }

            self.adapters_page.upload_csv(self.adapters_page.CSV_FILE_NAME, client_details)
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.fill_filter(self.adapters_page.CSV_ADAPTER_QUERY)
            self.devices_page.enter_search()
            self.devices_page.wait_for_table_to_load()
            assert self.devices_page.count_entities() > 0
            self.devices_page.wait_for_spinner_to_end()
            self.devices_page.click_expand_cell(
                cell_index=self.devices_page.count_sort_column(self.devices_page.FIELD_LAST_SEEN))
            last_seen_rows = self.devices_page.get_expand_cell_column_data(self.devices_page.FIELD_LAST_SEEN,
                                                                           self.devices_page.FIELD_LAST_SEEN)
            last_seen_rows_copy = last_seen_rows.copy()
            last_seen_rows_copy.sort(key=lambda date: datetime.strptime(date, '%Y-%m-%d %H:%M:%S'), reverse=True)
            assert last_seen_rows == last_seen_rows_copy
            self.adapters_page.clean_adapter_servers(CSV_NAME, True)
        self.wait_for_adapter_down(CSV_PLUGIN_NAME)
