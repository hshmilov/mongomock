from flaky import flaky

from services.adapters.csv_service import CsvService
from test_credentials.test_csv_credentials import \
    client_details as csv_client_details
from ui_tests.tests.ui_test_base import TestBase

CSV_ADAPTER_QUERY = 'adapters_data.csv_adapter.id == exists(true)'
CSV_FILE_NAME = 'csv'
CSV_NAME = 'CSV Serials'
QUERY_WIZARD_CSV_DATE_PICKER_VALUE = '2018-12-30 02:13:24.485Z'


class TestAdapters(TestBase):
    # Sometimes upload file to CSV adapter does not work
    @flaky(max_runs=2)
    def test_upload_csv_file(self):
        try:
            with CsvService().contextmanager(take_ownership=True):
                self.adapters_page.wait_for_adapter(CSV_NAME)
                self.adapters_page.click_adapter(CSV_NAME)
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.wait_for_table_to_load()
                self.adapters_page.click_new_server()
                self.adapters_page.upload_file_by_id(CSV_FILE_NAME, csv_client_details[CSV_FILE_NAME].file_contents)
                self.adapters_page.fill_creds(user_id=CSV_FILE_NAME)
                self.adapters_page.click_save()
                self.base_page.run_discovery()
                self.devices_page.switch_to_page()
                self.devices_page.fill_filter(CSV_ADAPTER_QUERY)
                self.devices_page.enter_search()
                self.devices_page.wait_for_table_to_load()
                assert self.devices_page.count_entities() > 0
                self.adapters_page.switch_to_page()
                self.adapters_page.clean_adapter_servers(CSV_NAME, True)
        finally:
            self.adapters_page.wait_for_adapter_down(CSV_NAME)

    # Sometimes upload file to CSV adapter does not work
    @flaky(max_runs=2)
    def test_query_wizard_include_outdated_adapter_devices(self):
        try:
            with CsvService().contextmanager(take_ownership=True):
                self.adapters_page.wait_for_adapter(CSV_NAME)
                self.adapters_page.click_adapter(CSV_NAME)
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.wait_for_table_to_load()
                self.adapters_page.click_new_server()
                self.adapters_page.upload_file_by_id(CSV_FILE_NAME, csv_client_details[CSV_FILE_NAME].file_contents)
                self.adapters_page.fill_creds(user_id=CSV_FILE_NAME)
                self.adapters_page.click_save()
                self.base_page.run_discovery()
                self.devices_page.switch_to_page()
                self.devices_page.click_query_wizard()
                self.devices_page.select_query_adapter(CSV_NAME)
                self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN)
                self.devices_page.select_query_comp_op('<')
                self.devices_page.fill_query_wizard_date_picker(QUERY_WIZARD_CSV_DATE_PICKER_VALUE)
                self.devices_page.close_datepicker()
                self.devices_page.click_search()
                self.devices_page.wait_for_table_to_load()
                assert self.devices_page.count_entities() == 1
                self.devices_page.click_query_wizard()
                self.devices_page.click_wizard_outdated_toggle()
                self.devices_page.click_search()
                self.devices_page.wait_for_table_to_load()
                assert self.devices_page.count_entities() == 2
                self.adapters_page.switch_to_page()
                self.adapters_page.clean_adapter_servers(CSV_NAME, True)
        finally:
            self.adapters_page.wait_for_adapter_down(CSV_NAME)
