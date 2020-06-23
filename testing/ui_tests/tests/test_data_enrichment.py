from test_credentials.test_esx_credentials import esx_json_file_mock_devices
from ui_tests.pages.adapters_page import JSON_NAME
from ui_tests.tests.ui_test_base import TestBase


class TestDataEnrichment(TestBase):
    def test_ip_to_location_enrichment(self):
        self.adapters_page.add_server(esx_json_file_mock_devices, JSON_NAME)
        self.adapters_page.wait_for_server_green()
        self.adapters_page.wait_for_table_to_load()
        self.adapters_page.wait_for_data_collection_toaster_absent()
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.find_checkbox_by_label('Enable device location mapping').click()

        self._upload_and_check_msg(upload_data='10.0.0.0/8,Iceland\r\n192.168.0.0/16, Greenland',
                                   msg='Uploaded CSV file does not have the required headers')
        self._upload_and_check_msg(upload_data='Subnet,Location\r\n10.0.a.0/8,Iceland\r\n192.168.0.0/16, Greenland',
                                   msg='Uploaded CSV file is not in the desired format')
        self._upload_and_check_msg(upload_data='Subnet,Location\r\n10.0.0.0/8,Iceland\r\n192.168.0.0/16, Greenland',
                                   msg='Saved Successfully')

        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.edit_columns(add_col_names=['Network Interfaces: Locations'])
        devices_table = self.devices_page.get_all_data()
        assert any('Greenland' in device for device in devices_table)

        # Cleanup
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.find_checkbox_by_label('Enable device location mapping').click()
        self.settings_page.click_save_global_settings()
        self.adapters_page.restore_json_client()

    def _upload_and_check_msg(self, upload_data, msg):
        csv_element = self.driver.find_element_by_css_selector(self.settings_page.CSV_IP_TO_LOCATION_SELECTOR)
        self.settings_page.upload_file_on_element(csv_element, upload_data)
        self.settings_page.click_save_global_settings()
        self.settings_page.wait_for_element_present_by_text(msg)
