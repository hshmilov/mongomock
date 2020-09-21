from axonius.utils.wait import wait_until
from services.adapters.csv_service import CsvService
from test_credentials.test_aws_sm_credentials import AWS_SECRETS_MANAGER, AWS_SECRETS_MANAGER_NAME, \
    AWS_SECRETS_MANAGER_SECRET_KEY
from test_credentials.test_csv_credentials import client_details as csv_client_details
from ui_tests.tests.ui_consts import CSV_NAME, CSV_PLUGIN_NAME
from ui_tests.tests.ui_test_base import TestBase


class TestAWSIntegration(TestBase):

    def _create_new_connection_with_vault(self, name=AWS_SECRETS_MANAGER_NAME,
                                          secret_key=AWS_SECRETS_MANAGER_SECRET_KEY, is_negative_test=False):
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_adapter(CSV_NAME)
        self.adapters_page.click_adapter(CSV_NAME)
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.wait_for_table_to_load()
        # add new connection
        self.adapters_page.click_new_server()
        self.adapters_page.fill_upload_csv_form_with_csv(self.adapters_page.CSV_FILE_NAME, csv_client_details)
        self.adapters_page.fetch_password_from_aws_vault(name=name,
                                                         secret_key=secret_key,
                                                         is_negative_test=is_negative_test)

        if is_negative_test:
            self.adapters_page.click_cancel()
        else:
            self.adapters_page.wait_for_element_present_by_text(self.adapters_page.SAVE_AND_FETCH_BUTTON)
            self.adapters_page.click_save_and_fetch()
            self.adapters_page.wait_for_data_collection_toaster_start()
            self.adapters_page.wait_for_data_collection_toaster_absent()

    def test_fetch_secret_key_field_from_vault(self):
        self.settings_page.enable_aws_vault_global_config(AWS_SECRETS_MANAGER)
        with CsvService().contextmanager(take_ownership=True):
            self._create_new_connection_with_vault()
            wait_until(lambda: self.devices_page.check_csv_device_count() > 0)
            self.adapters_page.clean_adapter_servers(CSV_NAME, True)
        self.wait_for_adapter_down(CSV_PLUGIN_NAME)

    def test_invalid_secret_id(self):
        """
        use case : unknown/invalid secert server ID will result in Failure icon for password fetch
        and submit button disabled as no password fetch from vault - on new client connection.
        """
        self.settings_page.enable_aws_vault_global_config(AWS_SECRETS_MANAGER)
        with CsvService().contextmanager(take_ownership=True):
            self._create_new_connection_with_vault(name='666', secret_key='666', is_negative_test=True)
            self.adapters_page.clean_adapter_servers(CSV_NAME, True)
        self.wait_for_adapter_down(CSV_PLUGIN_NAME)

    def test_password_input_when_vault_enabled(self):
        """
        use case : test basic client connection (regular) when vault enable in global config
        """
        self.settings_page.enable_aws_vault_global_config(AWS_SECRETS_MANAGER)
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

    def teardown_method(self, method):
        self.settings_page.clear_enterprise_password_mgmt_settings()
        super().teardown_method(method)
