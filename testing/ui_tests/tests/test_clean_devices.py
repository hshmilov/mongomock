import copy
import time
import datetime

from test_credentials.test_ad_credentials import ad_client1_details
from ui_tests.tests.adapters_test_base import AdapterTestBase
from ui_tests.tests.ui_consts import AD_ADAPTER_NAME


class TestCleanDB(AdapterTestBase):
    """
    Test clean db based on AX-4840 (https://axonius.atlassian.net/browse/AX-4840)
    """

    def _get_ad_device_count(self) -> int:
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()
        self.devices_page.select_query_adapter(AD_ADAPTER_NAME)
        self.devices_page.click_search()
        return self.devices_page.get_table_count()

    def test_clean_db(self):
        """
        Actions:
            - Execute initial discovery
            - Check in device page that devices were fetched
            - Execute discovery again
                - verify all devices from latter step still exist
            - Change configuration on AD adapter,
                - remove connection credentials (so devices won't be fetched again)
                - update last seen to 0 so all devices should be deleted
            - Execute discovery again
                - verify all devices from Microsoft AD were deleted
        """
        try:
            # === Step 1 === #
            self.dashboard_page.switch_to_page()
            self.base_page.run_discovery()
            # === Step 2 === #
            initial_count = self._get_ad_device_count()
            # === Step 3 === #
            self.base_page.run_discovery()
            assert initial_count == self._get_ad_device_count()
            # === Step 4 === #
            self.adapters_page.switch_to_page()
            self.adapters_page.clean_adapter_servers(AD_ADAPTER_NAME)
            self.adapters_page.wait_for_table_to_load()
            self.adapters_page.click_new_server()
            self.fill_ad_creds_with_junk()
            self.adapters_page.click_save()
            self.adapters_page.wait_for_spinner_to_end()
            self.adapters_page.wait_for_problem_connecting_try_again()
            self.adapters_page.wait_for_server_red()
            self.adapters_page.wait_for_data_collection_failed_toaster_absent()
            update_result = self.axonius_system.get_devices_db().update_many(
                {'adapters.plugin_name': 'active_directory_adapter'},
                {'$set': {'adapters.$.data.last_seen': datetime.datetime.now() - datetime.timedelta(hours=24)}})
            assert update_result.modified_count > 0
            self.dashboard_page.switch_to_page()
            self.dashboard_page.refresh()
            self.dashboard_page.wait_for_spinner_to_end()
            time.sleep(10)
            self.base_page.run_discovery()
            assert initial_count == self._get_ad_device_count()
            self._set_last_seen(1)
            # === Step 5 === #
            self.dashboard_page.switch_to_page()
            self.dashboard_page.refresh()
            self.dashboard_page.wait_for_spinner_to_end()
            time.sleep(10)
            self.base_page.run_discovery()
            count = self._get_ad_device_count()
            assert self._get_ad_device_count() == 0
        # always revert AD adapter
        finally:
            self.adapters_page.switch_to_page()
            self.adapters_page.clean_adapter_servers(AD_ADAPTER_NAME)
            self.adapters_page.wait_for_table_to_load()
            self.adapters_page.click_new_server()
            details = copy.copy(ad_client1_details)
            details.pop('use_ssl')
            self.adapters_page.fill_creds(**details)
            self.adapters_page.click_save()
            self.adapters_page.wait_for_server_green()
            self._set_last_seen('')
            self.dashboard_page.switch_to_page()
            self.dashboard_page.refresh()
            self.dashboard_page.wait_for_spinner_to_end()
            time.sleep(10)
            self.base_page.run_discovery()

    def _set_last_seen(self, value):
        self.adapters_page.switch_to_page()
        self.adapters_page.click_adapter(AD_ADAPTER_NAME)
        self.adapters_page.click_advanced_settings()
        self.adapters_page.click_advanced_configuration()  # move to advanced configuration
        self.adapters_page.fill_text_field_by_element_id('last_seen_threshold_hours', value=value)
        self.adapters_page.save_advanced_settings()
        self.adapters_page.wait_for_spinner_to_end()
