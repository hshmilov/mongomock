# pylint: disable=R0915
import time

from ui_tests.tests.ui_test_base import TestBase
from test_credentials.test_ad_credentials import ad_client1_details, ad_client2_details


class TestStopDiscovery(TestBase):
    def test_stop_discovery(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery(wait=False)
        self.base_page.stop_discovery()

    def test_stop_discovery_after_full_cycle(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.base_page.run_discovery(wait=False)
        self.base_page.stop_discovery()

    def test_stop_discovery_sanity(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_spinner_to_end()
        time.sleep(1)
        # For some reason it does not switch to adapters page every time in this stage
        self.adapters_page.switch_to_page()
        # Add AD clients.
        self.adapters_page.add_server(ad_client1_details)
        self.adapters_page.add_server(ad_client2_details)

        # Wait for discovery to start.
        self.base_page.run_discovery(wait=False)
        self.base_page.wait_for_stop_research()
        time.sleep(10)

        # Stop discovery
        self.base_page.stop_discovery()

        # Removing TestSecDomain, edit and save the TestDomain
        self.adapters_page.remove_server(ad_client2_details)
        self.adapters_page.click_row()
        self.adapters_page.click_save()
        self.adapters_page.wait_for_server_green()
        self.adapters_page.wait_for_table_to_load()
        self.adapters_page.wait_for_data_collection_toaster_absent()

        # Remove And re-add == TestDomain
        self.adapters_page.remove_server(ad_client1_details)
        self.adapters_page.add_server(ad_client1_details)
        self.adapters_page.wait_for_server_green()
        self.adapters_page.wait_for_table_to_load()
        self.adapters_page.wait_for_data_collection_toaster_absent()
