import copy

from selenium.common.exceptions import NoSuchElementException

from axonius.utils.wait import wait_until
from services.adapters.nexpose_service import NexposeService
from services.standalone_services.cyberark_vault_simulator_service import \
    CyberarkVaultSimulatorService
from test_credentials.test_nexpose_credentials import \
    client_details as nexpose_client_details
from testing.test_credentials.test_cyberark_vault_credentials import \
    CYBERARK_TEST_MOCK
from ui_tests.tests.ui_test_base import TestBase

GOOD_QUERY = r'Safe=Test;Folder=root\OS\Windows;Object=windows1'

NEXPOSE_NAME = 'Rapid7 Nexpose'
NEXPOSE_ADAPTER_FILTER = 'adapters == "nexpose_adapter"'
NEXPOSE_PLUGIN_NAME = 'nexpose_adapter'


class TestCyberarkIntegration(TestBase):
    def input_test_settings(self, app_id=CYBERARK_TEST_MOCK['application_id']):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.set_cyberark_vault_settings_enabled()
        self.settings_page.fill_cyberark_domain_address(CYBERARK_TEST_MOCK['domain'])
        self.settings_page.fill_cyberark_port(CYBERARK_TEST_MOCK['port'])
        self.settings_page.fill_cyberark_application_id(app_id)
        self.settings_page.fill_cyberark_cert_key(CYBERARK_TEST_MOCK['certificate_key'].file_contents)
        self.settings_page.click_save_button()
        self.settings_page.wait_for_saved_successfully_toaster()

    def remove_cyberark_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_checkbox_by_label(self.settings_page.USE_CYBERARK_VAULT)
        self.settings_page.click_toggle_button(toggle, make_yes=False, scroll_to_toggle=False)
        self.settings_page.click_save_button()

    def test_input_settings(self):
        with CyberarkVaultSimulatorService().contextmanager(take_ownership=True):
            self.input_test_settings()

        self.remove_cyberark_settings()

    def _wait_until_cyberark_is_present(self):
        self.adapters_page.refresh()
        self.adapters_page.click_adapter(NEXPOSE_NAME)
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.wait_for_table_to_load()
        self.adapters_page.click_new_server()
        element = self.adapters_page.driver.find_element_by_id('cyberark-button')
        assert element is not None

    def _check_device_count(self):
        self.devices_page.switch_to_page()
        self.devices_page.refresh()
        self.devices_page.run_filter_query(NEXPOSE_ADAPTER_FILTER)
        return self.devices_page.count_entities()

    def _check_fetch(self, should_succeed=True):
        cyberark_icon_element = self.adapters_page.driver.find_element_by_css_selector('.cyberark-icon .md-icon')
        class_attribute = 'success' if should_succeed else 'error'
        assert class_attribute in cyberark_icon_element.get_attribute('class')

    def test_successful_get(self):
        try:
            with CyberarkVaultSimulatorService().contextmanager(take_ownership=True), NexposeService().contextmanager(
                    take_ownership=True):
                self.input_test_settings()
                self.adapters_page.switch_to_page()
                self.adapters_page.wait_for_adapter(NEXPOSE_NAME)
                try:

                    self._input_query_string()
                    # Check successful vault fetch
                    wait_until(self._check_fetch, check_return_value=False, tolerated_exceptions_list=[AssertionError])
                    # Check successful device fetch.
                    self.adapters_page.click_save()
                    self.adapters_page.wait_for_spinner_to_end()
                    self.base_page.run_discovery()
                    wait_until(lambda: self._check_device_count() > 1, total_timeout=200, interval=20)

                finally:
                    self.adapters_page.clean_adapter_servers(NEXPOSE_NAME, delete_associated_entities=True)
        finally:
            self.wait_for_adapter_down(NEXPOSE_PLUGIN_NAME)
            self.remove_cyberark_settings()

    def _input_query_string(self, query=GOOD_QUERY):
        wait_until(self._wait_until_cyberark_is_present, check_return_value=False,
                   tolerated_exceptions_list=[AssertionError, NoSuchElementException])
        nexpose_client_copy = copy.deepcopy(nexpose_client_details)
        nexpose_client_copy.pop('password')
        self.adapters_page.fill_creds(**nexpose_client_copy)
        self.adapters_page.click_cyberark_button()
        self.adapters_page.fill_text_field_by_element_id('cyberark-query',
                                                         query)
        self.adapters_page.click_button('Fetch')

    def test_regular_password_input(self):
        try:
            with CyberarkVaultSimulatorService().contextmanager(take_ownership=True), NexposeService().contextmanager(
                    take_ownership=True):
                self.input_test_settings()
                self.adapters_page.switch_to_page()
                self.adapters_page.wait_for_adapter(NEXPOSE_NAME)
                try:

                    wait_until(self._wait_until_cyberark_is_present, check_return_value=False,
                               tolerated_exceptions_list=[AssertionError, NoSuchElementException])
                    self.adapters_page.fill_creds(**nexpose_client_details)

                    # Check successful device fetch.
                    self.adapters_page.click_save()
                    self.adapters_page.wait_for_spinner_to_end()
                    self.base_page.run_discovery()
                    wait_until(lambda: self._check_device_count() > 1, total_timeout=200, interval=20)

                finally:
                    self.adapters_page.clean_adapter_servers(NEXPOSE_NAME, delete_associated_entities=True)
        finally:
            self.wait_for_adapter_down(NEXPOSE_PLUGIN_NAME)
            self.remove_cyberark_settings()

    def test_bad_query(self):
        try:
            with CyberarkVaultSimulatorService().contextmanager(take_ownership=True), NexposeService().contextmanager(
                    take_ownership=True):
                self.input_test_settings()
                self.adapters_page.switch_to_page()
                self.adapters_page.wait_for_adapter(NEXPOSE_NAME)

                self._input_query_string(query='TestThis')
                # Check failing vault fetch
                wait_until(lambda: self._check_fetch(should_succeed=False), check_return_value=False,
                           tolerated_exceptions_list=[AssertionError])
                # Check validation fail.
                element = self.adapters_page.find_element_by_text(self.adapters_page.SAVE_AND_CONNECT_BUTTON)
                assert self.adapters_page.is_element_disabled(element)
                self.adapters_page.click_cancel()
        finally:
            self.wait_for_adapter_down(NEXPOSE_PLUGIN_NAME)
            self.remove_cyberark_settings()

    def test_bad_appid(self):
        try:
            with CyberarkVaultSimulatorService().contextmanager(take_ownership=True), NexposeService().contextmanager(
                    take_ownership=True):
                self.input_test_settings(app_id='bad_app_id')
                self.adapters_page.switch_to_page()
                self.adapters_page.wait_for_adapter(NEXPOSE_NAME)

                self._input_query_string()
                # Check failing vault fetch
                wait_until(lambda: self._check_fetch(should_succeed=False), check_return_value=False,
                           tolerated_exceptions_list=[AssertionError])
                # Check validation fail.
                element = self.adapters_page.find_element_by_text(self.adapters_page.SAVE_AND_CONNECT_BUTTON)
                assert self.adapters_page.is_element_disabled(element)
                self.adapters_page.click_cancel()
        finally:
            self.wait_for_adapter_down(NEXPOSE_PLUGIN_NAME)
            self.remove_cyberark_settings()

    def test_no_connection_during_discovery(self):
        try:
            with NexposeService().contextmanager(take_ownership=True):
                with CyberarkVaultSimulatorService().contextmanager(take_ownership=True):
                    self.input_test_settings()
                    self.adapters_page.switch_to_page()
                    self.adapters_page.wait_for_adapter(NEXPOSE_NAME)
                    self._input_query_string()
                    # Check successful vault fetch
                    wait_until(self._check_fetch, check_return_value=False, tolerated_exceptions_list=[AssertionError])
                    # Check successful device fetch.
                    self.adapters_page.click_save()
                    self.base_page.run_discovery()
                    wait_until(lambda: self._check_device_count() > 1, total_timeout=200, interval=20)

                self.base_page.run_discovery()
                self.adapters_page.switch_to_page()
                self.adapters_page.wait_for_adapter(NEXPOSE_NAME)
                self.adapters_page.refresh()
                self.adapters_page.click_adapter(NEXPOSE_NAME)
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.wait_for_table_to_load()
                self.adapters_page.wait_for_server_red()
                self.adapters_page.click_row()

                # check cyberark fetch
                self._check_fetch(should_succeed=False)
                self.adapters_page.is_query_error()
                assert CYBERARK_TEST_MOCK['domain'] in self.adapters_page.find_server_error()
                self.adapters_page.click_cancel()
        finally:
            self.adapters_page.clean_adapter_servers(NEXPOSE_NAME, delete_associated_entities=True)
            self.wait_for_adapter_down(NEXPOSE_PLUGIN_NAME)
            self.remove_cyberark_settings()
