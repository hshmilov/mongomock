from services.adapters.alertlogic_service import AlertlogicService
from services.adapters.aws_service import AwsService
from services.adapters.csv_service import CsvService
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import (ALERTLOGIC_ADAPTER,
                                      ALERTLOGIC_ADAPTER_NAME,
                                      AWS_ADAPTER,
                                      AWS_ADAPTER_NAME, CSV_NAME, CSV_PLUGIN_NAME)
from test_credentials.test_csv_credentials import client_details as csv_client_details


class TestDataForm(TestBase):
    ALERTLOGIC_INPUT = {
        'domain': 'publicapi.alertlogic.axon.net',
        'apikey': 'rubbish',
        'https_proxy': '18.18.18.18',
        'verify_ssl': True
    }
    S3_SECRET_FIELD_ID = 's3_secret_access_key'

    def verify_connection_changes(self, data_to_verify):
        self.adapters_page.wait_for_adapter(CSV_NAME)
        self.adapters_page.click_adapter(CSV_NAME)
        self.verify_adapter_connection_and_cancel(data_to_verify)

    def sync_on_server_connection_failure(self, adapter_plugin_name, domain):
        self.adapters_page.wait_for_element_present_by_text(domain)
        self.adapters_page.wait_for_problem_connecting_to_server()
        self.adapters_page.refresh()
        self.adapters_page.wait_for_adapter(adapter_plugin_name)
        self.adapters_page.click_adapter(adapter_plugin_name)
        self.adapters_page.wait_for_element_present_by_text(domain)

    def verify_adapter_connection(self, kwargs):
        self.adapters_page.click_row()
        self.adapters_page.verify_creds(**kwargs)

    def verify_adapter_connection_and_save(self, kwargs):
        self.verify_adapter_connection(kwargs)
        self.adapters_page.click_save_and_fetch()

    def verify_adapter_connection_and_cancel(self, kwargs):
        self.verify_adapter_connection(kwargs)
        self.adapters_page.click_cancel()

    def test_alertlogicservice_default_data(self):
        with AlertlogicService().contextmanager(take_ownership=True):
            self.adapters_page.create_new_adapter_connection(plugin_title=ALERTLOGIC_ADAPTER_NAME,
                                                             adapter_input=self.ALERTLOGIC_INPUT)
            self.sync_on_server_connection_failure(ALERTLOGIC_ADAPTER_NAME, self.ALERTLOGIC_INPUT.get('domain'))
            self.verify_adapter_connection_and_save(self.ALERTLOGIC_INPUT)
            self.sync_on_server_connection_failure(ALERTLOGIC_ADAPTER_NAME, self.ALERTLOGIC_INPUT.get('domain'))
            self.verify_adapter_connection_and_cancel(self.ALERTLOGIC_INPUT)
            self.adapters_page.clean_adapter_servers(ALERTLOGIC_ADAPTER_NAME)
        self.wait_for_adapter_down(ALERTLOGIC_ADAPTER)

    def test_aws_default_data(self):
        adapter_input = {
            'region_name': 'US-EAST-2',
            'aws_access_key_id': '123456789',
            'account_tag': 'axonius',
            'aws_secret_access_key': '987654321',
            'get_all_regions': True
        }

        with AwsService().contextmanager(take_ownership=True):
            self.adapters_page.create_new_adapter_connection(plugin_title=AWS_ADAPTER_NAME,
                                                             adapter_input=adapter_input)
            self.sync_on_server_connection_failure(AWS_ADAPTER_NAME, adapter_input.get('region_name'))
            self.verify_adapter_connection_and_save(adapter_input)
            self.sync_on_server_connection_failure(AWS_ADAPTER_NAME, adapter_input.get('region_name'))
            self.verify_adapter_connection_and_cancel(adapter_input)

            # Cleanup.
            self.adapters_page.clean_adapter_servers(AWS_ADAPTER_NAME)
        self.wait_for_adapter_down(AWS_ADAPTER)

    def test_clear_optional_password_field(self):
        with CsvService().contextmanager(take_ownership=True):
            csv_details = {
                **csv_client_details,
                self.S3_SECRET_FIELD_ID: '1234567'
            }
            self.adapters_page.upload_csv(self.adapters_page.CSV_FILE_NAME, csv_details, wait_for_toaster=True)
            self.adapters_page.switch_to_page()
            self.verify_connection_changes({self.S3_SECRET_FIELD_ID: '1234567'})
            self.adapters_page.click_row()
            self.adapters_page.fill_text_by_element(self.driver.find_element_by_id(self.S3_SECRET_FIELD_ID), '')
            self.adapters_page.click_save_and_fetch()
            self.adapters_page.wait_for_data_collection_toaster_start()
            self.adapters_page.wait_for_data_collection_toaster_absent()
            self.adapters_page.switch_to_page()
            self.verify_connection_changes({self.S3_SECRET_FIELD_ID: ''})

            self.adapters_page.clean_adapter_servers(CSV_NAME)
        self.wait_for_adapter_down(CSV_PLUGIN_NAME)
