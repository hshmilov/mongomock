from axonius.consts.metric_consts import Adapters
from services.adapters.ad_service import AdService
from services.adapters.cisco_service import CiscoService
from services.adapters.gotoassist_service import GotoassistService
from test_credentials.test_ad_credentials import ad_client1_details
from ui_tests.tests.adapters_test_base import AdapterTestBase
from ui_tests.tests.ui_consts import AD_ADAPTER_NAME

GOTOASSIST_NAME = 'RescueAssist'
GOTOASSIST_PLUGIN_NAME = 'gotoassist_adapter'


class TestAdaptersConnectivity(AdapterTestBase):
    def fill_gotoassist_creds_with_junk(self):
        self.adapters_page.fill_creds(client_id='asdf',
                                      user_name='password',
                                      password='password',
                                      client_secret='password')

    def fill_cisco_creds_with_junk(self):
        self.adapters_page.fill_creds(host='asdf',
                                      community='asdf')

    def test_connectivity(self):
        try:
            with GotoassistService().contextmanager(take_ownership=True):
                self.adapters_page.wait_for_adapter(GOTOASSIST_NAME)
                self.adapters_page.click_adapter(GOTOASSIST_NAME)
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.wait_for_table_to_load()
                self.adapters_page.click_new_server()
                self.fill_gotoassist_creds_with_junk()
                self.adapters_page.click_test_connectivity()

                # Goto assist return success for any creds
                self.adapters_page.wait_for_connect_valid()
                self.adapters_page.click_cancel()

            with CiscoService().contextmanager(take_ownership=True):
                self.adapters_page.wait_for_adapter(self.CISCO_NAME)
                self.adapters_page.click_adapter(self.CISCO_NAME)
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.wait_for_table_to_load()
                self.adapters_page.click_new_server()
                self.fill_cisco_creds_with_junk()
                self.adapters_page.click_test_connectivity()

                self.adapters_page.wait_for_test_connectivity_not_supported()
                self.adapters_page.click_cancel()

            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_spinner_to_end()

            self.adapters_page.click_adapter(AD_ADAPTER_NAME)
            self.adapters_page.wait_for_spinner_to_end()
            self.adapters_page.wait_for_table_to_load()
            self.adapters_page.click_new_server()
            self.fill_ad_creds_with_junk()
            self.adapters_page.click_test_connectivity()

            # Goto assist return success for any creds
            self.adapters_page.wait_for_problem_connecting_to_server()

            self.adapters_page.click_cancel()
        finally:
            self.adapters_page.clean_adapter_servers(GOTOASSIST_NAME)
            self.adapters_page.clean_adapter_servers(self.CISCO_NAME)
            self.wait_for_adapter_down(GOTOASSIST_PLUGIN_NAME)
            self.wait_for_adapter_down(self.CISCO_PLUGIN_NAME)

    def test_icon_color(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_spinner_to_end()
        try:
            self.adapters_page.clean_adapter_servers(AD_ADAPTER_NAME)
            self.adapters_page.wait_for_data_collection_toaster_absent()
            try:

                self.adapters_page.add_server(ad_client1_details)
                self.adapters_page.wait_for_server_green()

                self.adapters_page.switch_to_page()
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.search(AD_ADAPTER_NAME)
                self.adapters_page.wait_for_adapter_green()
            finally:
                self.adapters_page.clean_adapter_servers(AD_ADAPTER_NAME)

            try:
                self.adapters_page.click_new_server()
                self.fill_ad_creds_with_junk()
                self.adapters_page.click_save()
                self.adapters_page.wait_for_server_red()

                ad_log_tester = AdService().log_tester
                ad_log_tester.is_metric_in_log(metric_name=Adapters.CREDENTIALS_CHANGE_ERROR, value='.*')

                self.adapters_page.switch_to_page()

                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.search(AD_ADAPTER_NAME)
                self.adapters_page.wait_for_adapter_warning()
            finally:
                self.adapters_page.clean_adapter_servers(AD_ADAPTER_NAME)
        finally:
            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_spinner_to_end()
            self.adapters_page.add_server(ad_client1_details)
            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
