from ui_tests.tests.ui_test_base import TestBase


class AdapterTestBase(TestBase):

    AD_PRIMARY_DC_NAME = 'asdfasdf'
    AD_PRIMARY_USER = 'asdf'
    AD_PRIMARY_PASSWORD = 'asdf'
    AD_PRIMARY_DNS_ADDRESS = 'asdf.net'

    CISCO_NAME = 'Cisco'
    CISCO_PLUGIN_NAME = 'cisco_adapter'

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
