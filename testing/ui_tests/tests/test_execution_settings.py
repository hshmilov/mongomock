import time

from axonius.utils.wait import wait_until
from services.plugins.general_info_service import GeneralInfoService
from test_credentials.test_ad_credentials import ad_client1_details
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.pages.adapters_page import AD_NAME


class TestExecutionSettings(TestBase):
    def test_execution_settings(self):
        def check_execution(should_execute):
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_load()
            assert bool([x for x in self.devices_page.get_column_data(self.devices_page.FIELD_TAGS) if
                         x in ['Hostname Conflict', 'Execution Failure']]) == should_execute

        general_info_service = GeneralInfoService()

        with general_info_service.contextmanager(take_ownership=True):
            # Turn execution on and off
            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            self.settings_page.wait_for_spinner_to_end()
            toggle = self.settings_page.find_execution_toggle()
            self.settings_page.click_toggle_button(toggle, make_yes=True, scroll_to_toggle=False)
            self.settings_page.click_save_button()
            self.settings_page.find_saved_successfully_toaster()
            self.settings_page.click_global_settings()
            self.settings_page.wait_for_spinner_to_end()
            toggle = self.settings_page.find_execution_toggle()
            self.settings_page.click_toggle_button(toggle, make_yes=False, scroll_to_toggle=False)
            self.settings_page.click_save_button()
            self.settings_page.find_saved_successfully_toaster()

            # Add AD server
            self.adapters_page.add_server(ad_client1_details)
            self.base_page.run_discovery()

            time.sleep(60 * 5)
            check_execution(False)

            # Turn execution On
            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            self.settings_page.wait_for_spinner_to_end()
            toggle = self.settings_page.find_execution_toggle()
            self.settings_page.click_toggle_button(toggle, make_yes=True, scroll_to_toggle=False)
            self.settings_page.click_save_button()
            self.settings_page.find_saved_successfully_toaster()
            self.base_page.run_discovery()

            wait_until(lambda: check_execution(True), total_timeout=60 * 5, exc_list=[AssertionError],
                       check_return_value=False)

        # Cleanup
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.wait_for_spinner_to_end()
        toggle = self.settings_page.find_execution_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=False, scroll_to_toggle=False)
        self.settings_page.click_save_button()
        self.adapters_page.clean_adapter_servers(AD_NAME, delete_associated_entities=True)
        self.adapters_page.wait_for_table_to_load()
        self.adapters_page.add_server(ad_client1_details)
