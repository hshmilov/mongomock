import time
from copy import copy

from flaky import flaky
from selenium.common.exceptions import NoSuchElementException

from services.adapters.cisco_service import CiscoService
from services.adapters.gotoassist_service import GotoassistService
from test_credentials.test_ad_credentials import ad_client1_details
from ui_tests.pages.page import X_BODY
from ui_tests.tests.ui_test_base import TestBase

JSON_ADAPTER_SEARCH = 'json'
JSON_ADAPTER_TEXT_FROM_DESCRIPTION = 'formatted'
JSON_ADAPTER_NAME = 'JSON File'
JSON_ADAPTER_PLUGIN_NAME = 'json_file_adapter'

GOTOASSIST_NAME = 'GoToAssist'
CISCO_NAME = 'Cisco'
AD_NAME = 'Active Directory'


class TestAdapters(TestBase):
    def fill_gotoassist_creds_with_junk(self):
        self.adapters_page.fill_creds(client_id='asdf',
                                      user_name='password',
                                      password='password',
                                      client_secret='password')

    def fill_cisco_creds_with_junk(self):
        self.adapters_page.fill_creds(host='asdf',
                                      community='asdf')

    def fill_ad_creds_with_junk(self):
        self.adapters_page.fill_creds(user='asdf',
                                      password='asdf',
                                      dc_name='asdfasdf',
                                      dns_server_address='asdf.net')

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

    def wait_for_adapter(self, adapter_name, retires=60 * 3, interval=2):
        for _ in range(retires):
            self.alert_page.switch_to_page()
            self.adapters_page.switch_to_page()
            try:
                element = self.adapters_page.find_element_by_text(adapter_name)
                if element:
                    return
            except NoSuchElementException:
                pass
            time.sleep(interval)

    def wait_for_adapter_down(self, adapter_name, retires=60 * 3, interval=2):
        for _ in range(retires):
            self.alert_page.switch_to_page()
            self.adapters_page.switch_to_page()
            try:
                element = self.adapters_page.find_element_by_text(adapter_name)
                if element:
                    time.sleep(interval)
                    continue
            except NoSuchElementException:
                return
        assert False, 'Adapter still up'

    def test_connectivity(self):
        try:
            with GotoassistService().contextmanager(take_ownership=True):
                self.wait_for_adapter(GOTOASSIST_NAME)
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
                self.wait_for_adapter(CISCO_NAME)
                self.adapters_page.click_adapter(CISCO_NAME)
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.wait_for_table_to_load()
                self.adapters_page.click_new_server()
                self.fill_cisco_creds_with_junk()
                self.adapters_page.click_test_connectivity()

                self.adapters_page.wait_for_test_connectivity_not_supported()
                self.adapters_page.click_cancel()

            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_spinner_to_end()

            self.adapters_page.click_adapter(AD_NAME)
            self.adapters_page.wait_for_spinner_to_end()
            self.adapters_page.wait_for_table_to_load()
            self.adapters_page.click_new_server()
            self.fill_ad_creds_with_junk()
            self.adapters_page.click_test_connectivity()

            # Goto assist return success for any creds
            self.adapters_page.wait_for_problem_connecting_to_server()

            self.adapters_page.click_cancel()
        finally:
            self.wait_for_adapter_down(GOTOASSIST_NAME)
            self.wait_for_adapter_down(CISCO_NAME)

    @flaky(max_runs=2)
    def test_connections(self):
        try:
            with CiscoService().contextmanager(take_ownership=True):
                self.wait_for_adapter(CISCO_NAME)
                try:
                    self.adapters_page.click_adapter(CISCO_NAME)
                    self.adapters_page.wait_for_spinner_to_end()
                    for i in range(30):
                        self.adapters_page.click_new_server()
                        self.adapters_page.fill_creds(host=f'asdf{i}', community='asdf')
                        self.adapters_page.click_save()

                    element = self.adapters_page.find_element_by_text('asdf0')
                    self.adapters_page.scroll_into_view(element, X_BODY)
                finally:
                    self.adapters_page.clean_adapter_servers(CISCO_NAME)
        finally:
            self.wait_for_adapter_down(CISCO_NAME)

    def add_ad_server(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.click_adapter(AD_NAME)
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.click_new_server()

        dict_ = copy(ad_client1_details)
        dict_.pop('use_ssl')

        self.adapters_page.fill_creds(**dict_)
        self.adapters_page.click_save()

    def test_icon_color(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_spinner_to_end()
        try:
            self.adapters_page.clean_adapter_servers(AD_NAME)
            self.adapters_page.wait_for_data_collection_toaster_absent()
            try:

                self.add_ad_server()
                self.adapters_page.wait_for_server_green()

                self.adapters_page.switch_to_page()
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.search(AD_NAME)
                self.adapters_page.wait_for_adapter_green()
            finally:
                self.adapters_page.clean_adapter_servers(AD_NAME)

            try:
                self.adapters_page.click_new_server()
                self.fill_ad_creds_with_junk()
                self.adapters_page.click_save()
                self.adapters_page.wait_for_server_red()

                self.adapters_page.switch_to_page()

                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.search(AD_NAME)
                self.adapters_page.wait_for_adapter_orange()
            finally:
                self.adapters_page.clean_adapter_servers(AD_NAME)
        finally:
            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_spinner_to_end()
            self.add_ad_server()
            self.base_page.wait_for_stop_research()
            self.base_page.wait_for_run_research()
