from services.adapters.eset_service import EsetService
from services.adapters.gotoassist_service import GotoassistService
from test_credentials.test_eset_credentials import eset_details
from test_credentials.test_gotoassist_credentials import client_details
from ui_tests.tests.ui_test_base import TestBase

GOTOASSIST_NAME = 'RescueAssist'
ESET_NAME = 'ESET Endpoint Security'


class TestAdaptersPage(TestBase):
    def test_adapters_page_sanity(self):
        try:
            with GotoassistService().contextmanager(take_ownership=True):
                self.adapters_page.wait_for_adapter(GOTOASSIST_NAME)
                self.adapters_page.click_adapter(GOTOASSIST_NAME)
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.wait_for_table_to_load()
                self.adapters_page.click_new_server()
                self.adapters_page.fill_creds(**client_details)
                self.adapters_page.click_save()
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.switch_to_page()
                with EsetService().contextmanager(take_ownership=True):
                    self.adapters_page.wait_for_adapter(ESET_NAME)
                    self.adapters_page.click_adapter(ESET_NAME)
                    self.adapters_page.wait_for_spinner_to_end()
                    self.adapters_page.wait_for_table_to_load()
                    self.adapters_page.click_new_server()
                    self.adapters_page.fill_creds(**eset_details)
                    self.adapters_page.click_save()
                    self.adapters_page.wait_for_spinner_to_end()
                    self.base_page.wait_for_run_research()
                    self.base_page.run_discovery()
                    self.devices_page.switch_to_page()
                    self.devices_page.wait_for_table_to_load()
                    self.devices_page.click_query_wizard()
                    adapters_from_query_wizard = self.devices_page.get_query_adapters_list()
                    self.devices_page.close_dropdown()
                    assert adapters_from_query_wizard == sorted(adapters_from_query_wizard)
                    self.devices_page.close_dropdown()
                    self.devices_page.open_edit_columns()
                    adapters_from_edit_columns = self.devices_page.get_edit_columns_adapters_list()
                    assert adapters_from_edit_columns == sorted(adapters_from_edit_columns)
                    assert adapters_from_edit_columns == adapters_from_query_wizard
                    self.devices_page.close_dropdown()
                    self.devices_page.close_edit_columns()
                    self.adapters_page.switch_to_page()
                    self.adapters_page.clean_adapter_servers(GOTOASSIST_NAME)
                    self.adapters_page.clean_adapter_servers(ESET_NAME)
        finally:
            self.adapters_page.wait_for_adapter_down(GOTOASSIST_NAME)
            self.adapters_page.wait_for_adapter_down(ESET_NAME)
