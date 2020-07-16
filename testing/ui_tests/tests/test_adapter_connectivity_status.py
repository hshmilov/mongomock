from axonius.utils.wait import wait_until
from ui_tests.tests.adapters_test_base import AdapterTestBase
from ui_tests.tests.ui_consts import AD_ADAPTER_NAME, JSON_ADAPTER_NAME

from services.adapters.cisco_service import CiscoService


class TestAdaptersConnectivityStatus(AdapterTestBase):

    AD_SECONDARY_DC_NAME = 'blah'

    def test_clients_indicators(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.search(AD_ADAPTER_NAME)
        assert self.adapters_page.find_status_symbol_success()
        assert self.adapters_page.find_status_count_success() == 1

        self.insert_bad_client_to_ad()
        self.adapters_page.switch_to_page()
        assert self.adapters_page.find_status_symbol_error()
        assert self.adapters_page.find_status_symbol_success()
        assert self.adapters_page.find_status_count_success() == 1
        assert self.adapters_page.find_status_symbol_error()
        assert self.adapters_page.find_status_count_error() == 1

        self.insert_bad_client_to_ad(dc_name=self.AD_SECONDARY_DC_NAME)
        self.adapters_page.switch_to_page()
        assert self.adapters_page.find_status_symbol_error()
        wait_until(lambda: self.adapters_page.find_status_count_error() == 2)

        self.adapters_page.click_adapter(AD_ADAPTER_NAME)
        self.adapters_page.wait_for_table_to_be_responsive()
        self.adapters_page.switch_to_page()
        assert self.adapters_page.find_status_count_success() == 1

        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()
        self.adapters_page.switch_to_page()
        assert self.adapters_page.find_status_count_success() == 1

        # cleanup
        self.adapters_page.remove_server(ad_client={'dc_name': self.AD_SECONDARY_DC_NAME}, expected_left=2)
        self.adapters_page.remove_server(ad_client={'dc_name': self.AD_PRIMARY_DC_NAME}, expected_left=1)

    def test_adapters_filter_by_connection_status(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.verify_only_configured_adapters_visible()

        # spawn and kill Cisco adapter
        with CiscoService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(self.CISCO_NAME)
            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_spinner_to_end()
            adapters_count = self.adapters_page.get_adapters_table_length()
            configured_adapters_count = self.adapters_page.get_configured_adapters_count_from_switch_label()
            assert configured_adapters_count < adapters_count

            self.adapters_page.click_configured_adapters_filter_switch()
            self.adapters_page.verify_only_configured_adapters_visible()

            # Toggle state maintained after navigation
            self.adapters_page.click_adapter(JSON_ADAPTER_NAME)
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()
            self.adapters_page.switch_to_page()
            self.adapters_page.verify_only_configured_adapters_visible()

        self.wait_for_adapter_down(self.CISCO_PLUGIN_NAME)
