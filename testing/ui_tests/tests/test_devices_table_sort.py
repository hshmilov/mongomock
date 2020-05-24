from datetime import datetime
from datetime import timedelta

from axonius.utils.wait import wait_until
from test_helpers.file_mock_credentials import FileForCredentialsMock

from ui_tests.tests.ui_consts import CSV_NAME, CSV_PLUGIN_NAME
from ui_tests.tests.ui_test_base import TestBase

from testing.test_credentials.test_csv_credentials import CSV_FIELDS
from services.adapters.csv_service import CsvService
from test_credentials.test_csv_credentials import CSV_LIST, list_dict_to_csv


class TestDevicesTableSort(TestBase):

    def test_last_seen_table_sort(self):
        with CsvService().contextmanager(take_ownership=True):
            first_date = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
            second_date = (datetime.today() - timedelta(days=3)).strftime('%Y-%m-%d')
            third_date = (datetime.today() - timedelta(days=2)).strftime('%Y-%m-%d')

            CSV_LIST[0]['csv_Last_Seen'] = f'{first_date} 02:11:24.485Z'
            CSV_LIST[1]['csv_Last_Seen'] = f'{second_date} 02:11:24.485Z'
            CSV_LIST[2]['csv_Last_Seen'] = f'{third_date} 02:11:24.485Z'

            client_details = {
                'user_id': 'user',
                # an array of char
                self.adapters_page.CSV_FILE_NAME: FileForCredentialsMock(
                    'csv_name',
                    ','.join(CSV_FIELDS) + '\n' + list_dict_to_csv(CSV_LIST))
            }

            self.adapters_page.upload_csv(self.adapters_page.CSV_FILE_NAME, client_details)
            self.devices_page.switch_to_page()
            wait_until(lambda: self.devices_page.count_entities() == 2)
            self.devices_page.click_sort_column(self.devices_page.FIELD_LAST_SEEN)
            self.devices_page.wait_for_spinner_to_end()

            assert self.devices_queries_page.get_row_cell_text(row_index=1, cell_index=4) == CSV_LIST[0]['name']
            assert self.devices_queries_page.get_row_cell_text(row_index=2, cell_index=4) == CSV_LIST[2]['name']
            self.adapters_page.clean_adapter_servers(CSV_NAME, True)
        self.wait_for_adapter_down(CSV_PLUGIN_NAME)
