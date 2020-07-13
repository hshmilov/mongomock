from datetime import datetime, timedelta

from services.adapters.csv_service import CsvService
from test_credentials.test_csv_credentials import CSV_FIELDS
from test_helpers.file_mock_credentials import FileForCredentialsMock
from ui_tests.tests.test_adapters_connections import CSV_NAME
from ui_tests.tests.ui_consts import CSV_PLUGIN_NAME
from ui_tests.tests.ui_test_base import TestBase


class TestLastSeenExpandCellSort(TestBase):
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
