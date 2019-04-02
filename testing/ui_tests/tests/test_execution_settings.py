from axonius.utils.wait import wait_until
from services.plugins.general_info_service import GeneralInfoService
from test_credentials.test_ad_credentials import ad_client1_details
from ui_tests.tests.ui_test_base import TestBase


class TestExecutionSettings(TestBase):
    def test_execution_settings(self):
        def check_execution(should_execute):
            # Wait for WMI info
            self.devices_page.refresh()
            self.devices_page.wait_for_table_to_load()
            self.devices_page.switch_to_page()
            self.devices_page.fill_filter(self.devices_page.AD_WMI_ADAPTER_FILTER)
            self.devices_page.enter_search()
            self.devices_page.wait_for_table_to_load()
            assert bool(self.devices_page.get_all_data()) == should_execute

        general_info_service = GeneralInfoService()

        with general_info_service.contextmanager(take_ownership=True):
            # Add AD server
            self.adapters_page.add_server(ad_client1_details)
            self.base_page.run_discovery()

            check_execution(False)

            # Turn execution On
            self.enforcements_page.create_run_wmi_scan_on_each_cycle_enforcement()
            self.base_page.run_discovery()

            wait_until(lambda: check_execution(True), total_timeout=60 * 5, exc_list=[AssertionError],
                       check_return_value=False)
