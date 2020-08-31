import copy

from axonius.utils.wait import wait_until
from services.adapters.csv_service import CsvService
from test_credentials.test_csv_credentials import client_details as csv_client_details
from test_credentials.test_thycotic_vault_credentials import THYCOTIC_SECRET_SEREVER, \
    THYCOTIC_SECRET_SERVER_CSV_SECRET_ID, THYCOTIC_SECRET_SERVER_CSV_SECRET_KEY_ID
from ui_tests.tests.ui_consts import CSV_NAME, CSV_PLUGIN_NAME
from ui_tests.tests.ui_test_base import TestBase


class TestThycoticIntegration(TestBase):

    def _create_new_csv_connection_with_vault(self, secret_id=THYCOTIC_SECRET_SERVER_CSV_SECRET_ID,
                                              vault_field=None,
                                              is_negative_test=False):
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_adapter(CSV_NAME)
        self.adapters_page.click_adapter(CSV_NAME)
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.wait_for_table_to_load()
        # add new connection
        self.adapters_page.click_new_server()
        self.adapters_page.fill_upload_csv_form_with_csv(self.adapters_page.CSV_FILE_NAME, csv_client_details)
        self.adapters_page.fetch_password_from_thycotic_vault(secret_id=secret_id,
                                                              vault_field=vault_field,
                                                              is_negative_test=is_negative_test)

        if is_negative_test:
            self.adapters_page.click_cancel()
        else:
            self.adapters_page.wait_for_element_present_by_text(self.adapters_page.SAVE_AND_FETCH_BUTTON)
            self.adapters_page.click_save_and_fetch()
            self.adapters_page.wait_for_data_collection_toaster_start()
            self.adapters_page.wait_for_data_collection_toaster_absent()

    def test_fetch_secret_key_field_from_vault(self):
        self.settings_page.enable_thycotic_vault_global_config(THYCOTIC_SECRET_SEREVER)
        with CsvService().contextmanager(take_ownership=True):
            self._create_new_csv_connection_with_vault(secret_id=THYCOTIC_SECRET_SERVER_CSV_SECRET_KEY_ID,
                                                       vault_field='Secret Key')
            wait_until(lambda: self.devices_page.check_csv_device_count() > 0)
            self.adapters_page.clean_adapter_servers(CSV_NAME, True)
        self.wait_for_adapter_down(CSV_PLUGIN_NAME)

    def test_invalid_secret_id(self):
        """
        use case : unknown/invalid secert server ID will result in Failure icon for password fetch
        and submit button disabled as no password fetch from vault - on new client connection.
        """
        self.settings_page.enable_thycotic_vault_global_config(THYCOTIC_SECRET_SEREVER)
        with CsvService().contextmanager(take_ownership=True):
            self._create_new_csv_connection_with_vault(secret_id='666', is_negative_test=True)
            self.adapters_page.clean_adapter_servers(CSV_NAME, True)
        self.wait_for_adapter_down(CSV_PLUGIN_NAME)

    def test_password_input_when_vault_enabled(self):
        """
        use case : test basic client connection (regular) when vault enable in global config
        """
        self.settings_page.enable_thycotic_vault_global_config(THYCOTIC_SECRET_SEREVER)
        with CsvService().contextmanager(take_ownership=True, stop_grace_period='2'):
            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_adapter(CSV_NAME)
            self.adapters_page.click_adapter(CSV_NAME)
            self.adapters_page.open_add_edit_server(CSV_NAME)
            self.adapters_page.fill_upload_csv_form_with_csv(self.adapters_page.CSV_FILE_NAME, csv_client_details)
            self.adapters_page.click_save_and_fetch()
            self.adapters_page.wait_for_data_collection_toaster_start()
            self.adapters_page.wait_for_data_collection_toaster_absent()
            # Check successful device fetch.
            wait_until(lambda: self.devices_page.check_csv_device_count() > 0)

            # verify vault button not present after removed from config
            self.settings_page.clear_enterprise_password_mgmt_settings()
            self.adapters_page.switch_to_page()
            self.adapters_page.open_add_edit_server(CSV_NAME, row_position=1)
            wait_until(lambda: not self.adapters_page.is_save_button_disabled())
            self.adapters_page.verify_password_vault_button_not_present()
            self.adapters_page.click_cancel()
            self.adapters_page.clean_adapter_servers(CSV_NAME)

        self.wait_for_adapter_down(CSV_PLUGIN_NAME)

    def test_client_error_when_thycotic_host_timeout(self):
        """
        use case : when thycotic server is down adapter client with vault password  deice fetch
        will failed because we do not save password in db only the query
        """
        self.settings_page.enable_thycotic_vault_global_config(THYCOTIC_SECRET_SEREVER)
        with CsvService().contextmanager(take_ownership=True, stop_grace_period='2'):

            # step 1 = valid config
            self._create_new_csv_connection_with_vault()
            # Check successful device fetch.
            wait_until(lambda: self.devices_page.check_csv_device_count() > 0)

            # step 2 : update to invalid thycotic port and verify password fetch failed
            invalid_thycotic_server = copy.deepcopy(THYCOTIC_SECRET_SEREVER)
            invalid_thycotic_server['port'] = '9791'
            self.settings_page.enable_thycotic_vault_global_config(invalid_thycotic_server)

            # step 3 : verify password fetch error
            self.adapters_page.switch_to_page()
            self.adapters_page.open_add_edit_server(CSV_NAME)
            self.adapters_page.fetch_password_from_thycotic_vault(secret_id=THYCOTIC_SECRET_SERVER_CSV_SECRET_ID,
                                                                  is_negative_test=True)
            self.adapters_page.click_cancel()

            # step 4 : run discovery
            self.base_page.run_discovery()

            # step 5 : verify error msg on client connection edit .
            self.adapters_page.switch_to_page()
            self.adapters_page.open_add_edit_server(CSV_NAME, row_position=1)
            assert 'Failed to fetch password.' in self.adapters_page.find_server_error()
            self.adapters_page.click_cancel()
            self.adapters_page.clean_adapter_servers(CSV_NAME, True)
        self.wait_for_adapter_down(CSV_PLUGIN_NAME)

    def teardown_method(self, method):
        self.settings_page.clear_enterprise_password_mgmt_settings()
        super().teardown_method(method)
