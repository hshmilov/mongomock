from ui_tests.pages.adapters_page import AD_NAME
from ui_tests.tests.adapters_test_base import AdapterTestBase

from services.adapters.cisco_service import CiscoService

ERROR = 'error'
SUCCESS = 'success'

AD_SECONDARY_DC_NAME = 'blah'


class TestAdaptersConnectivityStatus(AdapterTestBase):

    AD_DC_NAME = AdapterTestBase.AD_PRIMARY_DC_NAME

    def _go_to_adapters_and_search_ad(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.search(AD_NAME)

    def _insert_bad_client_to_ad(self, dc_name=AD_DC_NAME):
        self.adapters_page.click_adapter(AD_NAME)
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.wait_for_table_to_load()

        # add new client - should fail to connect
        self.adapters_page.click_new_server()
        self.fill_ad_creds_with_junk(dc_name=dc_name)
        self.adapters_page.click_save()
        self.adapters_page.wait_for_element_absent_by_css(self.adapters_page.MODAL_OVERLAY_CSS)
        self.adapters_page.wait_for_element_present_by_text(dc_name)
        self.adapters_page.wait_for_problem_connecting_try_again()

    def test_clients_indicators(self):

        try:
            self._go_to_adapters_and_search_ad()
            assert self.adapters_page.find_status_symbol(status_type=SUCCESS)
            assert self.adapters_page.find_status_count(status_type=SUCCESS) == '1'

            self._insert_bad_client_to_ad()
            assert self.adapters_page.find_status_symbol(status_type=ERROR)

            self._go_to_adapters_and_search_ad()
            assert self.adapters_page.find_status_symbol(status_type=SUCCESS)
            assert self.adapters_page.find_status_count(status_type=SUCCESS) == '1'

            assert self.adapters_page.find_status_symbol(status_type=ERROR)
            assert self.adapters_page.find_status_count(status_type=ERROR) == '1'

            self._insert_bad_client_to_ad(dc_name=AD_SECONDARY_DC_NAME)
            assert self.adapters_page.find_status_symbol(status_type=ERROR)

            self._go_to_adapters_and_search_ad()
            assert self.adapters_page.find_status_count(status_type=ERROR) == '2'
        finally:
            # cleanup
            self.adapters_page.remove_server(ad_client={'dc_name': AD_SECONDARY_DC_NAME})
            self.adapters_page.wait_for_element_absent_by_text(AD_SECONDARY_DC_NAME)
            self.adapters_page.remove_server(ad_client={'dc_name': self.AD_DC_NAME})
            self.adapters_page.wait_for_element_absent_by_text(self.AD_DC_NAME)

    def test_adapters_filter_by_connection_status(self):

        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_spinner_to_end()

        table_len = self.adapters_page.get_adapters_table_length()
        count_label = self.adapters_page.get_connected_adapters_number_form_switch_label()

        assert int(count_label) <= table_len

        # spawn and kill Cisco adapter
        try:
            with CiscoService().contextmanager(take_ownership=True):
                self.adapters_page.wait_for_adapter(self.CISCO_NAME)
                self.adapters_page.switch_to_page()
                self.adapters_page.wait_for_spinner_to_end()
                table_len = self.adapters_page.get_adapters_table_length()
                count_label = self.adapters_page.get_connected_adapters_number_form_switch_label()

                assert int(count_label) < table_len

                self.adapters_page.click_connected_adapters_filter_switch()

                table_len = self.adapters_page.get_adapters_table_length()
                count_label = self.adapters_page.get_connected_adapters_number_form_switch_label()

                assert int(count_label) == table_len
        finally:
            self.wait_for_adapter_down(self.CISCO_PLUGIN_NAME)
