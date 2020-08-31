from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import AD_ADAPTER_NAME


class AdapterTestBase(TestBase):

    AD_PRIMARY_DC_NAME = 'asdfasdf'
    AD_PRIMARY_USER = 'asdf'
    AD_PRIMARY_PASSWORD = 'asdf'
    AD_PRIMARY_DNS_ADDRESS = 'asdf.net'

    CISCO_NAME = 'Cisco'
    CISCO_PLUGIN_NAME = 'cisco_adapter'

    def insert_bad_client_to_ad(self, dc_name=AD_PRIMARY_DC_NAME):
        self.adapters_page.click_adapter(AD_ADAPTER_NAME)
        self.adapters_page.wait_for_table_to_be_responsive()

        # add new client - should fail to connect
        self.adapters_page.click_new_server()
        self.fill_ad_creds_with_junk(dc_name=dc_name)
        self.adapters_page.click_save_and_fetch()
        self.adapters_page.wait_for_element_absent_by_css(self.adapters_page.MODAL_OVERLAY_CSS)
        self.adapters_page.wait_for_element_present_by_text(dc_name)
        self.adapters_page.wait_for_problem_connecting_try_again()

    def fill_ad_creds_with_junk(self,
                                user=AD_PRIMARY_USER,
                                password=AD_PRIMARY_PASSWORD,
                                dc_name=AD_PRIMARY_DC_NAME,
                                dns_server_address=AD_PRIMARY_DNS_ADDRESS):
        self.adapters_page.fill_creds(
            user=user,
            password=password,
            dc_name=dc_name,
            dns_server_address=dns_server_address)
