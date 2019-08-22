import re

from axonius.consts.metric_consts import Adapters
from axonius.utils.wait import wait_until
from services.adapters.ad_service import AdService
from services.adapters.cisco_service import CiscoService
from test_credentials.test_ad_credentials import ad_client1_details
from ui_tests.tests.ui_test_base import TestBase

JSON_ADAPTER_SEARCH = 'json'
JSON_ADAPTER_TEXT_FROM_DESCRIPTION = 'formatted'
JSON_ADAPTER_NAME = 'JSON File'
CISCO_NAME = 'Cisco'


class TestAdaptersFast(TestBase):
    def test_search(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.search(JSON_ADAPTER_SEARCH)
        adapter_list = self.adapters_page.get_adapter_list()

        assert len(adapter_list) == 1
        assert adapter_list[0].name == JSON_ADAPTER_NAME

        self.adapters_page.search(JSON_ADAPTER_TEXT_FROM_DESCRIPTION)
        adapter_list = self.adapters_page.get_adapter_list()
        assert not len(adapter_list), 'Search should work only on adapter name'

    def test_query_wizard_adapters_clients(self):
        with CiscoService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(CISCO_NAME)
            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_spinner_to_end()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.adapters_page.wait_for_table_to_load()
            self.devices_page.click_query_wizard()
            adapters = self.devices_page.get_query_adapters_list()
            # Cisco should not be in the adapters list because its dose not have a client
            assert CISCO_NAME not in adapters

    def test_add_server(self):
        self.adapters_page.add_server(ad_client1_details)
        ad_log_tester = AdService().log_tester
        assert ad_log_tester.is_metric_in_log(metric_name=Adapters.CREDENTIALS_CHANGE_OK,
                                              value=re.escape(ad_client1_details['dc_name']))
        pattern = f'"metric_name": "{Adapters.CREDENTIALS_CHANGE_OK}".*"ui_user": "admin", "ui_user_source": "internal"'
        wait_until(lambda: ad_log_tester.is_pattern_in_log(pattern))
