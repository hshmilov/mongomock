import time

from flaky import flaky

from services.adapters.cisco_service import CiscoService
from ui_tests.pages.page import PAGE_BODY
from ui_tests.tests.ui_test_base import TestBase

JSON_ADAPTER_SEARCH = 'json'
JSON_ADAPTER_TEXT_FROM_DESCRIPTION = 'formatted'
JSON_ADAPTER_NAME = 'JSON File'
JSON_ADAPTER_PLUGIN_NAME = 'json_file_adapter'
CSV_ADAPTER_QUERY = 'adapters_data.csv_adapter.id == exists(true)'
CSV_FILE_NAME = 'csv'
GOTOASSIST_NAME = 'RescueAssist (GoToAssist)'
CISCO_NAME = 'Cisco'
CISCO_PLUGIN_NAME = 'cisco_adapter'
CSV_NAME = 'CSV'
ESET_NAME = 'ESET Endpoint Security'
QUERY_WIZARD_CSV_DATE_PICKER_VALUE = '2018-12-30 02:13:24.485Z'


class TestAdapters(TestBase):
    @flaky(max_runs=2)
    def test_connections(self):
        try:
            with CiscoService().contextmanager(take_ownership=True):
                self.adapters_page.wait_for_adapter(CISCO_NAME)
                try:
                    self.adapters_page.click_adapter(CISCO_NAME)
                    self.adapters_page.wait_for_spinner_to_end()
                    for i in range(30):
                        self.adapters_page.click_new_server()
                        self.adapters_page.fill_creds(host=f'asdf{i}', community='asdf')
                        self.adapters_page.click_save()

                        # this sleeps makes the mechanism more reliable
                        # https://axonius.atlassian.net/browse/AX-4553
                        time.sleep(1)

                    time.sleep(5)

                    element = self.adapters_page.find_element_by_text('asdf0')
                    self.adapters_page.scroll_into_view(element, PAGE_BODY)
                finally:
                    self.adapters_page.clean_adapter_servers(CISCO_NAME)
        finally:
            self.wait_for_adapter_down(CISCO_PLUGIN_NAME)
