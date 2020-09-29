# pylint: disable=R0915
import time

from test_credentials.test_ad_credentials import (ad_client1_details,
                                                  ad_client2_details)
from ui_tests.tests.ui_test_base import TestBase


class TestStopDiscoverySanity(TestBase):
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

        # Stop discovery
        self.base_page.stop_discovery()

        time.sleep(20)
        self.adapters_page.refresh()

        # Removing TestSecDomain, edit and save the TestDomain
        self.adapters_page.remove_server(ad_client2_details, expected_left=1)
        time.sleep(5)
        self.adapters_page.click_row()
        self.adapters_page.click_save_and_fetch()
        self.adapters_page.wait_for_server_green(retries=400)

        time.sleep(20)
        self.adapters_page.refresh()

        # Remove And re-add == TestDomain
        self.adapters_page.remove_server(ad_client1_details, expected_left=0)
        self.adapters_page.add_server(ad_client1_details)
        self.adapters_page.wait_for_server_green()
