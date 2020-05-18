from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException

from axonius.utils.wait import wait_until
from services.standalone_services.cyberark_vault_simulator_service import \
    CyberarkVaultSimulatorService
from services.adapters.csv_service import CsvService
from testing.test_credentials.test_cyberark_vault_credentials import \
    CYBERARK_TEST_MOCK
from test_credentials.test_csv_credentials import client_details as csv_client_details
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import CSV_NAME, CSV_PLUGIN_NAME


GOOD_QUERY = r'Safe=Test;Folder=root\OS\Windows;Object=windows1'

CSV_ADAPTER_FILTER = 'adapters == "csv_adapter"'
STOP_GRACE_PERIOD = '2'  # 2 seconds, we don't really care.


class TestCyberarkIntegration(TestBase):
    def input_test_settings(self, app_id=CYBERARK_TEST_MOCK['application_id']):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.set_vault_settings_enabled()
        self.settings_page.select_cyberark_secret_server()
        self.settings_page.fill_cyberark_domain_address(CYBERARK_TEST_MOCK['domain'])
        self.settings_page.fill_cyberark_port(CYBERARK_TEST_MOCK['port'])
        self.settings_page.fill_cyberark_application_id(app_id)
        self.settings_page.fill_cyberark_cert_key(CYBERARK_TEST_MOCK['certificate_key'].file_contents)
        self.settings_page.click_save_global_settings()
        self.settings_page.wait_for_saved_successfully_toaster()

    @staticmethod
    def _wait_until_click_intercepted(func):
        return wait_until(func,
                          tolerated_exceptions_list=[ElementClickInterceptedException], check_return_value=False)

    def remove_cyberark_settings(self):
        self._wait_until_click_intercepted(self.settings_page.switch_to_page)
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.wait_for_element_present_by_text(self.settings_page.ENTERPRISE_PASSWORD_MGMT_TEXT)
        toggle = self.settings_page.find_checkbox_by_label(self.settings_page.USE_PASSWORD_MGR_VAULT)
        self.settings_page.click_toggle_button(toggle, make_yes=False, scroll_to_toggle=False)
        self.settings_page.click_save_global_settings()

    def test_input_settings(self):
        with CyberarkVaultSimulatorService().contextmanager(take_ownership=True):
            self.input_test_settings()
        self.remove_cyberark_settings()

    def _wait_until_cyberark_is_present(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.refresh()
        self.adapters_page.click_adapter(CSV_NAME)
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.wait_for_table_to_load()
        self.adapters_page.click_new_server()

        element = None
        try:
            element = self.adapters_page.driver.find_element_by_id('cyberark-button')
        except NoSuchElementException:
            # dismiss the connection modal
            if element is None:
                self.adapters_page.click_cancel()
                raise

        assert element is not None

    @staticmethod
    def _cyberark_context_manager():
        cyberark = CyberarkVaultSimulatorService().contextmanager(take_ownership=True,
                                                                  stop_grace_period=STOP_GRACE_PERIOD)
        return cyberark

    @staticmethod
    def _csv_context_manager():
        csv = CsvService().contextmanager(take_ownership=True, stop_grace_period=STOP_GRACE_PERIOD)
        return csv

    def _check_device_count(self):
        self.devices_page.switch_to_page()
        self.devices_page.refresh()
        self.devices_page.run_filter_query(CSV_ADAPTER_FILTER)
        return self.devices_page.count_entities()

    def _did_fetch_succeed(self):
        cyberark_icon_element = self.adapters_page.driver.find_element_by_css_selector('.cyberark-icon .md-icon')
        options = {'success': True, 'error': False}
        for (k, retval) in options.items():
            if k in cyberark_icon_element.get_attribute('class'):
                return retval
        assert False, 'Can\'t find fetch result'
        return None

    def test_successful_get(self):
        with self._cyberark_context_manager(), self._csv_context_manager():
            print('Started the cyberark vault simulator.')
            self.input_test_settings()
            print('Saved cyberark settings.')
            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_adapter(CSV_NAME)

            self._input_query_string()
            # Check successful vault fetch
            print('Waiting for vault fetch.')
            assert self._did_fetch_succeed()
            # Check successful device fetch.
            self._wait_until_click_intercepted(self.adapters_page.click_save)
            self.adapters_page.wait_for_table_to_load()
            print('Running discovery.')
            self._wait_until_click_intercepted(self.base_page.run_discovery)
            print('Waiting for devices to appear.')
            wait_until(lambda: self._check_device_count() > 0, total_timeout=200, interval=5)
            self.adapters_page.clean_adapter_servers(CSV_NAME)

        print('Removing cyberark settings.')
        self.remove_cyberark_settings()
        self.wait_for_adapter_down(CSV_PLUGIN_NAME)

    def _input_query_string(self, query=GOOD_QUERY):
        print('Waiting until cyberark icon is present.')
        wait_until(self._wait_until_cyberark_is_present, check_return_value=False,
                   tolerated_exceptions_list=[AssertionError, NoSuchElementException])
        print('Adding csv client.')

        self.adapters_page.click_cyberark_button()
        self.adapters_page.fill_text_field_by_element_id('cyberark-query',
                                                         query)

        print('Fetching cyberark query.')
        self.adapters_page.click_button('Fetch')
        wait_until(self._did_fetch_succeed, check_return_value=False,
                   tolerated_exceptions_list=[AssertionError])

        self.adapters_page.fill_upload_csv_form_with_csv(self.adapters_page.CSV_FILE_NAME, csv_client_details)

    def test_regular_password_input(self):
        with self._cyberark_context_manager(), self._csv_context_manager():
            print('Started the cyberark vault simulator.')
            self.input_test_settings()
            print('Saved cyberark settings.')
            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_adapter(CSV_NAME)

            print('Waiting until cyberark icon is present.')
            wait_until(self._wait_until_cyberark_is_present, check_return_value=False,
                       tolerated_exceptions_list=[AssertionError, NoSuchElementException])
            print('Adding csv client.')
            self.adapters_page.fill_upload_csv_form_with_csv(self.adapters_page.CSV_FILE_NAME, csv_client_details)

            # Check successful device fetch.
            self._wait_until_click_intercepted(self.adapters_page.click_save)
            self.adapters_page.wait_for_table_to_load()
            print('Running discovery.')

            self._wait_until_click_intercepted(self.base_page.run_discovery)
            wait_until(lambda: self._check_device_count() > 0, total_timeout=200, interval=20)
            self.adapters_page.clean_adapter_servers(CSV_NAME)

        print('Removing cyberark settings.')
        self.remove_cyberark_settings()
        self.wait_for_adapter_down(CSV_PLUGIN_NAME)

    def test_bad_query(self):
        with self._cyberark_context_manager(), self._csv_context_manager():
            self.input_test_settings()
            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_adapter('CSV')

            self._input_query_string(query='TestThis')
            # Check failing vault fetch
            assert not self._did_fetch_succeed()
            self.adapters_page.click_cancel()
            self.adapters_page.clean_adapter_servers(CSV_NAME)

        self.remove_cyberark_settings()
        self.wait_for_adapter_down(CSV_PLUGIN_NAME)

    def test_bad_appid(self):
        with self._cyberark_context_manager(), self._csv_context_manager():
            self.input_test_settings(app_id='bad_app_id')
            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_adapter(CSV_NAME)

            self._input_query_string()
            # Check failing vault fetch
            assert not self._did_fetch_succeed()

            self.adapters_page.click_cancel()
            self.adapters_page.clean_adapter_servers(CSV_NAME)

        self.remove_cyberark_settings()
        self.wait_for_adapter_down(CSV_PLUGIN_NAME)

    def test_no_connection_during_discovery(self):
        print('starting test_no_connection_during_discovery')
        with self._csv_context_manager():
            with CyberarkVaultSimulatorService().contextmanager(take_ownership=True):
                print('Started the cyberark vault simulator.')
                self.input_test_settings()
                print('Saved cyberark settings.')
                self.adapters_page.switch_to_page()
                self.adapters_page.wait_for_adapter(CSV_NAME)
                self._input_query_string()
                # Check successful vault fetch
                print('waiting for check fetch')
                assert self._did_fetch_succeed()
                # Check successful device fetch.
                self.adapters_page.click_save()
                self.adapters_page.wait_for_table_to_load()
                print('Running discovery.')
                self.base_page.run_discovery()
                print('waiting for check device count')
                wait_until(lambda: self._check_device_count() > 0, total_timeout=200, interval=20)

            print('cyberark simulator is killed, done checking waiting for check device count.')
            self.base_page.run_discovery()
            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_adapter(CSV_NAME)
            self.adapters_page.refresh()
            self.adapters_page.click_adapter(CSV_NAME)
            self.adapters_page.wait_for_spinner_to_end()
            self.adapters_page.wait_for_table_to_load()
            self.adapters_page.wait_for_server_red()
            self.adapters_page.click_row()
            print('Got to red client.')

            # check cyberark fetch
            print('check fetch.')
            assert not self._did_fetch_succeed()
            self.adapters_page.is_query_error()
            assert CYBERARK_TEST_MOCK['domain'] in self.adapters_page.find_server_error()
            print('Canceling.')
            self.adapters_page.click_cancel()
            self.adapters_page.clean_adapter_servers(CSV_NAME)

        print('csv adapter is killed')
        self.remove_cyberark_settings()
        self.wait_for_adapter_down(CSV_PLUGIN_NAME)
