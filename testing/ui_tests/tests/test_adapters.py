import re
import time

from flaky import flaky
from selenium.common.exceptions import NoSuchElementException

from axonius.consts import adapter_consts
from axonius.utils.wait import wait_until
from services.adapters.ad_service import AdService
from services.adapters.cisco_service import CiscoService
from services.adapters.csv_service import CsvService
from services.adapters.eset_service import EsetService
from services.adapters.gotoassist_service import GotoassistService
from test_credentials.test_ad_credentials import ad_client1_details
from test_credentials.test_csv_credentials import \
    client_details as csv_client_details
from test_credentials.test_eset_credentials import eset_details
from test_credentials.test_gotoassist_credentials import client_details
from ui_tests.pages.adapters_page import AD_NAME
from ui_tests.pages.page import X_BODY
from ui_tests.tests.ui_consts import LOCAL_DEFAULT_USER_PATTERN
from ui_tests.tests.ui_test_base import TestBase

JSON_ADAPTER_SEARCH = 'json'
JSON_ADAPTER_TEXT_FROM_DESCRIPTION = 'formatted'
JSON_ADAPTER_NAME = 'JSON File'
JSON_ADAPTER_PLUGIN_NAME = 'json_file_adapter'
CSV_ADAPTER_QUERY = 'adapters_data.csv_adapter.id == exists(true)'
CSV_FILE_NAME = 'csv'
GOTOASSIST_NAME = 'GoToAssist'
CISCO_NAME = 'Cisco'
CSV_NAME = 'CSV Serials'
ESET_NAME = 'ESET Endpoint Security'
QUERY_WIZARD_CSV_DATE_PICKER_VALUE = '2018-12-30 02:13:24.485Z'


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

    def test_adapters_page_sanity(self):
        try:
            with GotoassistService().contextmanager(take_ownership=True):
                self.adapters_page.wait_for_adapter(GOTOASSIST_NAME)
                self.adapters_page.click_adapter(GOTOASSIST_NAME)
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.wait_for_table_to_load()
                self.adapters_page.click_new_server()
                self.adapters_page.fill_creds(**client_details)
                self.adapters_page.click_save()
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.switch_to_page()
                with EsetService().contextmanager(take_ownership=True):
                    self.adapters_page.wait_for_adapter(ESET_NAME)
                    self.adapters_page.click_adapter(ESET_NAME)
                    self.adapters_page.wait_for_spinner_to_end()
                    self.adapters_page.wait_for_table_to_load()
                    self.adapters_page.click_new_server()
                    self.adapters_page.fill_creds(**eset_details)
                    self.adapters_page.click_save()
                    self.adapters_page.wait_for_spinner_to_end()
                    self.base_page.wait_for_run_research()
                    self.base_page.run_discovery()
                    self.devices_page.switch_to_page()
                    self.devices_page.wait_for_table_to_load()
                    self.devices_page.click_query_wizard()
                    adapters_from_query_wizard = self.devices_page.get_query_adapters_list()
                    self.devices_page.close_dropdown()
                    assert adapters_from_query_wizard == sorted(adapters_from_query_wizard)
                    self.devices_page.close_dropdown()
                    self.devices_page.open_edit_columns()
                    adapters_from_edit_columns = self.devices_page.get_edit_columns_adapters_list()
                    assert adapters_from_edit_columns == sorted(adapters_from_edit_columns)
                    assert adapters_from_edit_columns == adapters_from_query_wizard
                    self.devices_page.close_dropdown()
                    self.devices_page.close_edit_columns()
                    self.adapters_page.switch_to_page()
                    self.adapters_page.clean_adapter_servers(GOTOASSIST_NAME)
                    self.adapters_page.clean_adapter_servers(ESET_NAME)
        finally:
            self.wait_for_adapter_down(GOTOASSIST_NAME)
            self.wait_for_adapter_down(ESET_NAME)

    # Sometimes upload file to CSV adapter does not work
    @flaky(max_runs=2)
    def test_upload_csv_file(self):
        try:
            with CsvService().contextmanager(take_ownership=True):
                self.adapters_page.wait_for_adapter(CSV_NAME)
                self.adapters_page.click_adapter(CSV_NAME)
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.wait_for_table_to_load()
                self.adapters_page.click_new_server()
                self.adapters_page.upload_file_by_id(CSV_FILE_NAME, csv_client_details[CSV_FILE_NAME].file_contents)
                self.adapters_page.fill_creds(user_id=CSV_FILE_NAME)
                self.adapters_page.click_save()
                self.base_page.run_discovery()
                self.devices_page.switch_to_page()
                self.devices_page.fill_filter(CSV_ADAPTER_QUERY)
                self.devices_page.enter_search()
                self.devices_page.wait_for_table_to_load()
                assert self.devices_page.count_entities() > 0
                self.adapters_page.switch_to_page()
                self.adapters_page.clean_adapter_servers(CSV_NAME, True)
        finally:
            self.wait_for_adapter_down(CSV_NAME)

    # Sometimes upload file to CSV adapter does not work
    @flaky(max_runs=2)
    def test_query_wizard_include_outdated_adapter_devices(self):
        try:
            with CsvService().contextmanager(take_ownership=True):
                self.adapters_page.wait_for_adapter(CSV_NAME)
                self.adapters_page.click_adapter(CSV_NAME)
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.wait_for_table_to_load()
                self.adapters_page.click_new_server()
                self.adapters_page.upload_file_by_id(CSV_FILE_NAME, csv_client_details[CSV_FILE_NAME].file_contents)
                self.adapters_page.fill_creds(user_id=CSV_FILE_NAME)
                self.adapters_page.click_save()
                self.base_page.run_discovery()
                self.devices_page.switch_to_page()
                self.devices_page.click_query_wizard()
                self.devices_page.select_query_adapter(CSV_NAME)
                self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN)
                self.devices_page.select_query_comp_op('<')
                self.devices_page.fill_query_wizard_date_picker(QUERY_WIZARD_CSV_DATE_PICKER_VALUE)
                # Sleep through the time it takes the date picker to react to the filled date
                time.sleep(0.5)
                self.devices_page.wait_for_table_to_load()
                self.devices_page.close_showing_results()
                self.devices_page.click_search()
                assert self.devices_page.count_entities() == 1
                self.devices_page.click_query_wizard()
                self.devices_page.click_wizard_outdated_toggle()
                self.devices_page.click_search()
                assert self.devices_page.count_entities() == 2
                self.adapters_page.switch_to_page()
                self.adapters_page.clean_adapter_servers(CSV_NAME, True)
        finally:
            self.wait_for_adapter_down(CSV_NAME)

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
                self.adapters_page.wait_for_adapter(CISCO_NAME)
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
                self.adapters_page.wait_for_adapter(CISCO_NAME)
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

    def test_icon_color(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_spinner_to_end()
        try:
            self.adapters_page.clean_adapter_servers(AD_NAME)
            self.adapters_page.wait_for_data_collection_toaster_absent()
            try:

                self.adapters_page.add_server(ad_client1_details)
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

                ad_log_tester = AdService().log_tester
                pattern = f'{LOCAL_DEFAULT_USER_PATTERN}: {adapter_consts.LOG_CLIENT_FAILURE_LINE}'
                ad_log_tester.is_pattern_in_log(re.escape(pattern))

                self.adapters_page.switch_to_page()

                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.search(AD_NAME)
                self.adapters_page.wait_for_adapter_orange()
            finally:
                self.adapters_page.clean_adapter_servers(AD_NAME)
        finally:
            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_spinner_to_end()
            self.adapters_page.add_server(ad_client1_details)

    @staticmethod
    def _are_ad_entities_present(page, field):
        page.switch_to_page()
        page.wait_for_table_to_load()
        page.run_filter_query(page.AD_ADAPTER_FILTER)
        page.wait_for_table_to_load()
        all_entity_field_values = page.get_column_data(field)
        return len(all_entity_field_values) > 1

    def _are_ad_devices_present(self):
        return self._are_ad_entities_present(self.devices_page, self.devices_page.FIELD_NETWORK_INTERFACES_IPS)

    def _are_ad_users_present(self):
        return self._are_ad_entities_present(self.users_page, self.users_page.FIELD_USERNAME_TITLE)

    def _check_ad_adapter_client_deletion(self, with_entities_deletion):
        # Prepare test
        assert wait_until(self._are_ad_devices_present)
        assert wait_until(self._are_ad_users_present)

        # Execute action

        self.adapters_page.clean_adapter_servers(AD_NAME, with_entities_deletion)

        # check action was executed

        if with_entities_deletion:
            wait_until(lambda: not self._are_ad_devices_present())
            wait_until(lambda: not self._are_ad_users_present())
        else:
            assert self._are_ad_devices_present()
            assert self._are_ad_users_present()

    def _check_delete_adapter(self, associated_entities):
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_spinner_to_end()
        try:
            try:
                self._check_ad_adapter_client_deletion(with_entities_deletion=associated_entities)
            finally:
                self.adapters_page.clean_adapter_servers(AD_NAME)
        finally:
            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_spinner_to_end()
            self.adapters_page.add_server(ad_client1_details)

    def test_delete_adapter_without_associated_entities(self):
        self.adapters_page.add_server(ad_client1_details)
        self._check_delete_adapter(False)

    def test_delete_adapter_with_associated_entities(self):
        self._check_delete_adapter(True)

    def test_add_server(self):
        self.adapters_page.add_server(ad_client1_details)
        ad_log_tester = AdService().log_tester
        pattern = f'{LOCAL_DEFAULT_USER_PATTERN}: {adapter_consts.LOG_CLIENT_SUCCESS_LINE}'
        ad_log_tester.is_pattern_in_log(re.escape(pattern))
