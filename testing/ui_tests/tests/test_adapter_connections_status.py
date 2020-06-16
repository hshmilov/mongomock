import pytest

from services.adapters.aws_service import AwsService
from services.adapters.csv_service import CsvService
from ui_tests.tests.adapters_test_base import AdapterTestBase
from ui_tests.tests.ui_consts import AWS_ADAPTER_NAME, AWS_ADAPTER, AD_ADAPTER_NAME, CSV_NAME, CSV_PLUGIN_NAME
from test_credentials.test_ad_credentials import ad_client1_details
from test_credentials.test_csv_credentials import client_details as csv_client_details


class TestAdapterConnectionStatus(AdapterTestBase):

    @pytest.mark.skip('ad change')
    def test_adapter_connection_status_panel(self):

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
            self.adapters_page.wait_for_spinner_to_end()
            self.adapters_page.wait_for_server_red()
            self.adapters_page.wait_for_data_collection_toaster_absent()

            self.adapters_page.wait_for_spinner_to_end()
            self.adapters_page.wait_for_data_collection_toaster_absent()

            with CsvService().contextmanager(take_ownership=True):
                self.adapters_page.upload_csv(self.adapters_page.CSV_FILE_NAME, csv_client_details)
                self.adapters_page.wait_for_data_collection_toaster_start()
                self.adapters_page.wait_for_data_collection_toaster_absent()

                # ad success
                self.adapters_page.add_server(ad_client1_details)
                self.adapters_page.wait_for_server_green()

                # ad fail
                self.adapters_page.click_new_server()
                self.fill_ad_creds_with_junk()
                self.adapters_page.click_save()
                self.adapters_page.wait_for_server_red()

                self.dashboard_page.switch_to_page()

                adapters = self.driver.find_elements_by_css_selector('.adapter-connections-status .adapter')
                icons = adapters[0].find_elements_by_css_selector('.x-icon')
                assert len(icons) == 1
                assert self.adapters_page.has_class(icons[0], 'icon-error')

                icons = adapters[1].find_elements_by_css_selector('.x-icon')
                assert len(icons) == 2
                assert self.adapters_page.has_class(icons[0], 'icon-error')
                assert self.adapters_page.has_class(icons[1], 'icon-success')

                icons = adapters[2].find_elements_by_css_selector('.x-icon')
                assert len(icons) == 1
                assert self.adapters_page.has_class(icons[0], 'icon-success')

                self.adapters_page.clean_adapter_servers(CSV_NAME)
            self.wait_for_adapter_down(CSV_PLUGIN_NAME)
            self.adapters_page.clean_adapter_servers(AD_ADAPTER_NAME)
            self.adapters_page.clean_adapter_servers(AWS_ADAPTER_NAME)
        self.wait_for_adapter_down(AWS_ADAPTER)
