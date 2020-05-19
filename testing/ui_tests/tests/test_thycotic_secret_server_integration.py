import copy

import pytest
import requests

from selenium.common.exceptions import NoSuchElementException

from axonius.utils.wait import wait_until
from services.adapters.esx_service import EsxService
from test_credentials.test_esx_credentials import client_details as esx_client_details
from test_credentials.test_thycotic_vault_credentials import THYCOTIC_SECRET_SEREVER,\
    THYCOTIC_SECRET_SEREVER__ESX_SECRET_ID
from ui_tests.tests.test_adapters import ESX_PLUGIN_NAME
from ui_tests.tests.ui_consts import AD_ADAPTER_NAME
from ui_tests.tests.ui_test_base import TestBase

ESX_ADAPTER_FILTER = 'adapters == "esx_adapter"'
ESX_ADAPTER_NAME = 'VMware ESXi'

ADAPTER_THYCOTIC_VAULT_BUTTION = 'cyberark-button'


class TestThycoticIntegration(TestBase):

    def _create_new_esx_connection_with_valid_vault(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_adapter(ESX_ADAPTER_NAME)
        self.adapters_page.click_adapter(ESX_ADAPTER_NAME)
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.wait_for_table_to_load()
        # add new connection
        esx_client_copy = copy.deepcopy(esx_client_details[0][0])
        esx_client_copy.pop('password')
        self.adapters_page.click_new_server()
        self.adapters_page.fill_creds(**esx_client_copy)
        self.adapters_page.fetch_password_from_thycotic_vault(screct_id=THYCOTIC_SECRET_SEREVER__ESX_SECRET_ID)
        self.adapters_page.wait_for_element_present_by_text(self.adapters_page.SAVE_AND_CONNECT_BUTTON)
        self.adapters_page.click_save()
        self.adapters_page.wait_for_data_collection_toaster_start()
        self.adapters_page.wait_for_data_collection_toaster_absent()

    def _open_esx_connection_in_edit_mode(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_adapter(ESX_ADAPTER_NAME)
        self.adapters_page.click_adapter(ESX_ADAPTER_NAME)
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.wait_for_table_to_load()
        self.adapters_page.click_edit_server()

    def _check_esx_device_count(self):
        self.devices_page.switch_to_page()
        self.devices_page.refresh()
        self.devices_page.run_filter_query(ESX_ADAPTER_FILTER)
        return self.devices_page.count_entities()

    @staticmethod
    def test_enable_thycotic_vault():
        # verify our beloved thycotic secret server is ALIVE
        resp = requests.get(url=f'{THYCOTIC_SECRET_SEREVER["host"]}/webservices/SSWebservice.asmx/VersionGet')
        resp.raise_for_status()

    def test_fetch_password_from_vault(self):
        self.settings_page.enable_thycotic_vault_global_config(THYCOTIC_SECRET_SEREVER)
        with EsxService().contextmanager(take_ownership=True):
            self._create_new_esx_connection_with_valid_vault()
            wait_until(lambda: self._check_esx_device_count() > 1, total_timeout=200, interval=20)
            self.adapters_page.clean_adapter_servers(ESX_ADAPTER_NAME, True)
        self.wait_for_adapter_down(ESX_PLUGIN_NAME)

    def test_invalid_secret_id(self):
        """
        use case : unknown/invalid secert server ID will result in Failure icon for password fetch
        and submit button disabled as no password fetch from vault - on new client connection.
        """

        self.settings_page.enable_thycotic_vault_global_config(THYCOTIC_SECRET_SEREVER)
        with EsxService().contextmanager(take_ownership=True):
            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_adapter(ESX_ADAPTER_NAME)
            self.adapters_page.click_adapter(ESX_ADAPTER_NAME)
            self.adapters_page.wait_for_spinner_to_end()
            self.adapters_page.wait_for_table_to_load()
            # add new connection
            esx_client_copy = copy.deepcopy(esx_client_details[0][0])
            esx_client_copy.pop('password')
            self.adapters_page.click_new_server()
            self.adapters_page.fill_creds(**esx_client_copy)
            # fetch from vault
            self.adapters_page.fetch_password_from_thycotic_vault(screct_id='invalid', is_negative_test=True)
            assert self.adapters_page.is_save_button_disabled()
            self.adapters_page.click_cancel()
            self.adapters_page.clean_adapter_servers(ESX_ADAPTER_NAME, True)
        self.wait_for_adapter_down(ESX_PLUGIN_NAME)

    def test_password_input_when_vault_enabled(self):
        """
        use case : test basic client connection (regular) when vault enable in global config
        """
        self.settings_page.enable_thycotic_vault_global_config(THYCOTIC_SECRET_SEREVER)
        with EsxService().contextmanager(take_ownership=True):
            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_adapter(ESX_ADAPTER_NAME)
            self.adapters_page.click_adapter(ESX_ADAPTER_NAME)
            self.adapters_page.wait_for_spinner_to_end()
            self.adapters_page.wait_for_table_to_load()
            # add new connection
            self.adapters_page.click_new_server()
            self.adapters_page.fill_creds(**esx_client_details[0][0])
            self.adapters_page.click_save()
            self.adapters_page.wait_for_data_collection_toaster_start()
            self.adapters_page.wait_for_data_collection_toaster_absent()
            # Check successful device fetch.
            wait_until(lambda: self._check_esx_device_count() > 1, total_timeout=200, interval=20)
            self.adapters_page.clean_adapter_servers(ESX_ADAPTER_NAME, True)
        self.wait_for_adapter_down(ESX_PLUGIN_NAME)

    @pytest.mark.skip('AX-7550')
    def test_client_error_when_thycotic_host_timeout(self):
        """
        use case : when thycotic server is down adapter client with vault password  deice fetch
        will failed because we do not save password in db only the query

        """
        self.settings_page.enable_thycotic_vault_global_config(THYCOTIC_SECRET_SEREVER)
        with EsxService().contextmanager(take_ownership=True):

            # step 1 = valid config
            self._create_new_esx_connection_with_valid_vault()
            # Check successful device fetch.
            wait_until(lambda: self._check_esx_device_count() > 1, total_timeout=200, interval=20)

            # step 2 : update to invalid thycotic port and verify password fetch failed
            invalid_thycotic_server = copy.deepcopy(THYCOTIC_SECRET_SEREVER)
            invalid_thycotic_server['port'] = '9791'
            self.settings_page.enable_thycotic_vault_global_config(invalid_thycotic_server)

            # step 3 : verify password fetch error
            self._open_esx_connection_in_edit_mode()
            self.adapters_page.fetch_password_from_thycotic_vault(screct_id=THYCOTIC_SECRET_SEREVER__ESX_SECRET_ID,
                                                                  is_negative_test=True)
            self.adapters_page.click_cancel()

            # step 4 : run discovery
            self.base_page.run_discovery()

            # step 5 : verify error msg on client connection edit .
            self._open_esx_connection_in_edit_mode()
            assert 'Connection refused' in self.adapters_page.find_server_error()
            assert invalid_thycotic_server['port'] in self.adapters_page.find_server_error()
            self.adapters_page.click_cancel()
            self.adapters_page.clean_adapter_servers(ESX_ADAPTER_NAME, True)
        self.wait_for_adapter_down(ESX_PLUGIN_NAME)

    def test_remove_thycotic_from_global_config(self):
        """
        test case : verify vault password fetch button disappear from client connection
        when enterprise password mgmt disabled on global config
        """
        self.settings_page.enable_thycotic_vault_global_config(THYCOTIC_SECRET_SEREVER)
        self.settings_page.clear_enterprise_password_mgmt_settings()
        # verify
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_adapter(AD_ADAPTER_NAME)
        self.adapters_page.click_adapter(AD_ADAPTER_NAME)
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.wait_for_table_to_load()
        self.adapters_page.click_new_server()

        wait_until(self.adapters_page.verify_thycotic_button_is_not_present,
                   check_return_value=True,
                   tolerated_exceptions_list=[NoSuchElementException])
        self.adapters_page.click_cancel()

    def teardown_method(self, method):
        self.settings_page.clear_enterprise_password_mgmt_settings()
        super().teardown_method(method)
