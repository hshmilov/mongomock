from json_file_adapter.service import FILE_NAME
from services.adapters.csv_service import CsvService
from test_credentials.test_aws_credentials_mock import aws_json_file_mock_devices
from test_credentials.test_csv_credentials import CSV_FIELDS
from test_helpers.file_mock_credentials import FileForCredentialsMock
from ui_tests.tests.ui_consts import LABEL_CLIENT_WITH_SAME_ID, CSV_PLUGIN_NAME, CSV_NAME
from ui_tests.tests.ui_test_base import TestBase


class TestDeviceProfile(TestBase):

    def test_device_profile(self):
        # JSON FILE - AWS mock
        aws_json_mock_with_label = aws_json_file_mock_devices.copy()
        aws_json_mock_with_label[FILE_NAME] = LABEL_CLIENT_WITH_SAME_ID
        aws_json_mock_with_label['connectionLabel'] = LABEL_CLIENT_WITH_SAME_ID
        self.adapters_page.add_json_server(aws_json_mock_with_label, run_discovery_at_last=True, position=2)

        with CsvService().contextmanager(take_ownership=True):
            # CSV

            client_details = {
                'user_id': 'user',
                LABEL_CLIENT_WITH_SAME_ID: FileForCredentialsMock(
                    'csv_name',
                    ','.join(CSV_FIELDS) +
                    f'\ndcny1.TestDomain.test,Serial1,Windows,,Office,02:11:24.485Z 02:11:24.485Z,10.0.2.99,10.0.2.99')
            }
            self.adapters_page.upload_csv(LABEL_CLIENT_WITH_SAME_ID, client_details, wait_for_toaster=True)

            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()

            self.devices_page.click_row()
            self.devices_page.click_general_tab()

            self.devices_page.click_tab(self.devices_page.FIELD_NETWORK_INTERFACES)

            self._assert_adapter_logos()

            self.devices_page.hover_entity_adapter_icon(index=0, clickable_rows=False)
            tooltip_table = self.devices_page.get_entity_adapter_tooltip_table()
            self._assert_adapter_logos_device1(parent=tooltip_table)
            self.devices_page.unhover_entity_adapter_icon()

            self.devices_page.hover_entity_adapter_icon(index=1, clickable_rows=False)
            tooltip_table = self.devices_page.get_entity_adapter_tooltip_table()
            self._assert_adapter_logos_device2(parent=tooltip_table)
            self.devices_page.unhover_entity_adapter_icon()

            self.devices_page.assert_csv_field_match_ui_data(self.devices_page.generate_csv_field(
                'devices',
                self.driver.current_url.split('/')[-1],
                self.devices_page.FIELD_NETWORK_INTERFACES_NAME
            ))

            self.adapters_page.clean_adapter_servers(CSV_NAME, True)

        self.wait_for_adapter_down(CSV_PLUGIN_NAME)
        self.adapters_page.remove_json_extra_server(aws_json_mock_with_label)

    def _assert_adapter_logos(self):
        table_rows = self.devices_page.get_all_table_rows_elements(parent=self.driver, clickable_rows=False)
        self._assert_adapter_logos_device1(table_rows[0])
        self._assert_adapter_logos_device2(table_rows[1])

    def _assert_adapter_logos_device1(self, parent):
        logos_row_1 = self.devices_page.get_column_data_adapter_names(parent=parent)
        assert len(logos_row_1) == 2
        assert logos_row_1 == ['active_directory_adapter', 'csv_adapter']

    def _assert_adapter_logos_device2(self, parent):
        logos_row_2 = self.devices_page.get_column_data_adapter_names(parent=parent)
        assert len(logos_row_2) == 1
        assert logos_row_2[0] == 'json_file_adapter'
