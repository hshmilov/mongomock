from axonius.utils.wait import wait_until
from test_credentials.test_ad_credentials import ad_client1_details
from ui_tests.pages.adapters_page import AD_NAME
from ui_tests.tests.ui_test_base import TestBase


class TestAdaptersDelete(TestBase):
    @staticmethod
    def _are_ad_entities_present(page):
        page.switch_to_page()
        page.wait_for_table_to_load()
        page.run_filter_query(page.AD_ADAPTER_FILTER)
        page.wait_for_table_to_load()
        return page.count_entities() > 0

    def _are_ad_devices_present(self):
        return self._are_ad_entities_present(self.devices_page)

    def _are_ad_users_present(self):
        return self._are_ad_entities_present(self.users_page)

    def _check_ad_adapter_client_deletion(self, with_entities_deletion):
        # Prepare test
        assert wait_until(self._are_ad_devices_present, total_timeout=60 * 10)
        assert wait_until(self._are_ad_users_present, total_timeout=60 * 10)

        # Execute action

        try:
            self.adapters_page.clean_adapter_servers(AD_NAME, with_entities_deletion)
            self.adapters_page.wait_for_spinner_to_end()

            # check action was executed

            if with_entities_deletion:
                wait_until(lambda: not self._are_ad_devices_present(), total_timeout=60 * 10)
                wait_until(lambda: not self._are_ad_users_present(), total_timeout=60 * 10)
            else:
                assert self._are_ad_devices_present()
                assert self._are_ad_users_present()

        finally:
            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_spinner_to_end()
            self.adapters_page.add_server(ad_client1_details)
            self.adapters_page.wait_for_server_green()

            # The discovery is here to make sure that the adapter is idle once we finish
            self.settings_page.switch_to_page()
            self.base_page.run_discovery()

    def test_delete_adapter_without_associated_entities(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self._check_ad_adapter_client_deletion(with_entities_deletion=False)

    def test_delete_adapter_with_associated_entities(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self._check_ad_adapter_client_deletion(with_entities_deletion=True)
