from axonius.utils.serial_csv.constants import MAX_ROWS_LEN
from services.adapters.csv_service import CsvService
from services.adapters.wmi_service import WmiService
from test_credentials.test_csv_credentials import CSV_FIELDS
from test_credentials.test_gui_credentials import DEFAULT_USER
from test_credentials.test_cylance_credentials import cylance_json_file_mock_credentials
from test_helpers.file_mock_credentials import FileForCredentialsMock
from ui_tests.pages.entities_page import CSV_TIMEOUT
from ui_tests.tests.test_entities_table import TestEntitiesTable
from ui_tests.tests.ui_consts import (AD_MISSING_AGENTS_QUERY_NAME, CSV_NAME,
                                      CSV_PLUGIN_NAME,
                                      DEVICES_SEEN_IN_LAST_7_DAYS_QUERY,
                                      LABEL_CLIENT_WITH_SAME_ID,
                                      WMI_ADAPTER_NAME, JSON_ADAPTER_NAME, JSON_ADAPTER_FILTER)


class TestDevicesTableMoreCases(TestEntitiesTable):

    def test_devices_last_seen_export_csv(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()

        self.devices_page.wait_for_csv_to_update_cache()

        # filter the ui to fit the QUERY_FILTER_DEVICES of the csv
        self.devices_page.add_query_last_seen_in_days(7)
        self.axonius_system.gui.login_user(DEFAULT_USER)
        result = self.axonius_system.gui.get_entity_view_csv('devices',
                                                             self.QUERY_FIELDS,
                                                             DEVICES_SEEN_IN_LAST_7_DAYS_QUERY,
                                                             timeout=CSV_TIMEOUT)
        self.devices_page.assert_csv_match_ui_data(result)

    def test_export_csv_config(self):
        """
        Check the export csv modal config:
        1 - Check that default values are appearing
        2 - When changing the default delimiter in config, see that it gets filled
        3 - Clean up the config and make sure default values are appearing again
        4 - If entering max rows value outside the range, see that it gets reset
        5 - Export the csv then open again and see that values are default
        :return:
        """

        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_csv_to_update_cache()

        # Check 1
        self._check_default_csv_config()

        # Check 2
        self._check_delimiter_setting_set()

        # Check 3
        self._check_delimiter_setting_reset()

        # Check 4
        self._check_max_rows_range()

        # Check 5
        self._check_csv_config_after_export()

    def test_devices_column_filter(self):
        host_name = 'CB First'
        asset_name = 'DCNY1'

        with CsvService().contextmanager(take_ownership=True):
            # CSV

            client_details = {
                'user_id': 'user',
                LABEL_CLIENT_WITH_SAME_ID: FileForCredentialsMock(
                    'csv_name',
                    ','.join(CSV_FIELDS) +
                    f'\n{asset_name},Serial1,Windows,,Office,02:11:24.485Z 02:11:24.485Z,10.0.2.99')
            }
            self.adapters_page.upload_csv(LABEL_CLIENT_WITH_SAME_ID, client_details)

            self.base_page.run_discovery()
            self.devices_page.switch_to_page()

            # link devices so we'll have 3 adapters connected to one device
            self.devices_page.click_row_checkbox(1, make_yes=True)
            self.devices_page.click_row_checkbox(2, make_yes=True)
            self.devices_page.open_link_dialog()
            self.devices_page.confirm_link()

            self.users_page.open_edit_columns()
            self.devices_page.remove_columns([self.devices_page.FIELD_LAST_SEEN,
                                              self.devices_page.FIELD_NETWORK_INTERFACES_MAC,
                                              self.devices_page.FIELD_NETWORK_INTERFACES_IPS,
                                              self.devices_page.FIELD_OS_TYPE,
                                              self.devices_page.FIELD_TAGS])
            self.devices_page.add_columns([self.devices_page.PREFERRED_HOSTNAME_FIELD])
            self.devices_page.close_edit_columns_save_user_default()
            self.devices_page.filter_column(self.devices_page.PREFERRED_HOSTNAME_FIELD,
                                            filter_list=[{'include': True, 'term': 'test'}])

            # filter hostname column, assert its tooltip
            self.devices_page.filter_column(self.devices_page.FIELD_HOSTNAME_TITLE,
                                            filter_list=[{'include': False, 'term': 'test'}])
            self.devices_page.click_expand_cell(row_index=1, cell_index=5)
            tooltips_rows = self.devices_page.get_expand_cell_column_data(self.devices_page.FIELD_HOSTNAME_TITLE,
                                                                          self.devices_page.FIELD_HOSTNAME_TITLE)
            assert tooltips_rows == [asset_name, host_name]
            self.devices_page.click_expand_cell(row_index=1, cell_index=5)

            # filter asset name column, assert its tooltip
            self.devices_page.filter_column(self.devices_page.FIELD_ASSET_NAME, adapter_list=[JSON_ADAPTER_NAME])
            self.devices_page.click_expand_cell(row_index=1, cell_index=4)
            tooltips_rows = self.devices_page.get_expand_cell_column_data(self.devices_page.FIELD_ASSET_NAME,
                                                                          self.devices_page.FIELD_ASSET_NAME)
            assert tooltips_rows == [asset_name, asset_name]
            self.devices_page.click_expand_cell(row_index=1, cell_index=4)

            table_first_row_data = self.devices_page.get_all_data_proper()[0]
            assert table_first_row_data['Host Name'] == host_name
            assert table_first_row_data['Asset Name'] == asset_name
            assert table_first_row_data['Preferred Host Name'].strip() == ''

            # remove network interfaces: IPs to avoid +x remainder that doesn't match the csv
            remove_network_ips = {'specific_data.data.network_interfaces.ips': [{'include': False, 'term': ''}]}

            excluded_adapters = {'specific_data.data.name': ['json_file_adapter']}
            field_filters = {'specific_data.data.hostname': [{'include': False, 'term': 'test'}, remove_network_ips]}

            fields = 'adapters,specific_data.data.name,specific_data.data.hostname,' \
                     'specific_data.data.hostname_preferred'
            self.axonius_system.gui.login_user(DEFAULT_USER)
            result = self.axonius_system.gui.get_entity_view_csv('devices',
                                                                 fields,
                                                                 excluded_adapters=excluded_adapters,
                                                                 field_filters=field_filters,
                                                                 timeout=CSV_TIMEOUT)

            self.devices_page.assert_csv_match_ui_data(result, max_rows=20)

            self.adapters_page.clean_adapter_servers(CSV_NAME, True)

        self.wait_for_adapter_down(CSV_PLUGIN_NAME)

    def _check_default_csv_config(self):
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.open_export_csv()
        assert self.devices_page.is_csv_config_matching_default_fields()
        self.devices_page.close_csv_config_dialog()

    def _check_delimiter_setting_set(self):
        self.settings_page.set_csv_delimiter('B')
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.open_export_csv()
        assert self.devices_page.get_csv_delimiter_field() == 'B'

    def _check_delimiter_setting_reset(self):
        self.devices_page.close_csv_config_dialog()
        self.settings_page.set_csv_delimiter('')
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.open_export_csv()
        assert self.devices_page.is_csv_config_matching_default_fields()

    def _check_max_rows_range(self):
        self.devices_page.set_csv_max_rows_field(MAX_ROWS_LEN + 1)
        self.devices_page.key_down_tab()
        assert self.devices_page.get_csv_max_rows_field() == MAX_ROWS_LEN
        self.devices_page.set_csv_max_rows_field(-1)
        self.devices_page.key_down_tab()
        assert self.devices_page.get_csv_max_rows_field() == 1

    def _check_csv_config_after_export(self):
        self.devices_page.confirm_csv_config_dialog()
        self.devices_page.wait_for_export_csv_button_visible()
        self.devices_page.open_export_csv()
        assert self.devices_page.is_csv_config_matching_default_fields()

    def test_devices_save_query(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()

        self.devices_page.customize_view_and_save('test_save_query', 50, self.devices_page.FIELD_HOSTNAME_TITLE,
                                                  [],
                                                  [self.devices_page.FIELD_LAST_SEEN, self.devices_page.FIELD_OS_TYPE],
                                                  JSON_ADAPTER_FILTER)
        view_data = self.devices_page.get_all_data()

        # Load some default view, to change it and test the saved view's influence
        self.devices_page.execute_saved_query(AD_MISSING_AGENTS_QUERY_NAME)
        assert self.devices_page.get_all_data() != view_data

        self.devices_page.clear_filter()
        self.devices_page.execute_saved_query('test_save_query')

        # Check loaded data is equal to original one whose view was saved
        assert self.devices_page.get_all_data() == view_data

    def test_wmi_info_shown(self):
        self.enforcements_page.switch_to_page()
        with WmiService().contextmanager(take_ownership=True):
            self.enforcements_page.create_run_wmi_scan_on_each_cycle_enforcement()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.click_query_wizard()
            adapters = self.devices_page.get_query_adapters_list()
            # WMI Info should be in the adapters list because its does have a client
            assert WMI_ADAPTER_NAME in adapters

    def test_devices_delete(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()

        self.devices_page.delete_devices(JSON_ADAPTER_FILTER)

    def test_device_hover(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_gui_settings()
        self.settings_page.wait_for_spinner_to_end()
        default_num_of_val_per_col = self.settings_page.find_values_count_per_column()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.query_hostname_contains('CB First')
        remainder_value = self.devices_page.hover_remainder(row_index=1, cell_index=self.devices_page.count_sort_column(
            self.devices_page.FIELD_NETWORK_INTERFACES_IPS))
        tooltip_header = self.devices_page.get_tooltip_table_head()
        assert tooltip_header == self.devices_page.FIELD_NETWORK_INTERFACES_IPS
        num_of_devices_in_tooltip = len(self.devices_page.get_tooltip_table_data())
        assert remainder_value == num_of_devices_in_tooltip - default_num_of_val_per_col

    def change_values_count_per_column_to_be_val(self, val):
        self.settings_page.switch_to_page()
        self.settings_page.click_gui_settings()
        self.settings_page.wait_for_spinner_to_end()
        self.settings_page.select_values_count_per_column(val)
        self.settings_page.click_save_gui_settings()
        self.settings_page.wait_for_saved_successfully_toaster()

    def test_change_values_count_per_column(self):
        self.change_values_count_per_column_to_be_val('1')
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.query_hostname_contains('CB First')
        remainder_value = self.devices_page.hover_remainder(row_index=1,
                                                            cell_index=self.devices_page.count_sort_column(
                                                                self.devices_page.FIELD_NETWORK_INTERFACES_IPS))
        tooltip_header = self.devices_page.get_tooltip_table_head()
        assert tooltip_header == self.devices_page.FIELD_NETWORK_INTERFACES_IPS
        num_of_devices_in_tooltip = len(self.devices_page.get_tooltip_table_data())
        assert remainder_value == num_of_devices_in_tooltip - int(1)
        # reset to default value
        self.change_values_count_per_column_to_be_val('2')

    def test_column_filter_with_complex_field(self):
        self.adapters_page.add_json_server(cylance_json_file_mock_credentials, run_discovery_at_last=False,
                                           last_seen_threshold_hours='0')
        self.devices_page.switch_to_page()

        fields = 'specific_data.data.agent_versions.adapter_name,specific_data.data.agent_versions'
        field_filters = {'specific_data.data.agent_versions.adapter_name': [{'include': True, 'term': 'aaaaaa'}]}
        self.axonius_system.gui.login_user(DEFAULT_USER)
        result = self.axonius_system.gui.get_entity_view_csv('devices', fields, field_filters=field_filters)
        assert result == b'\xef\xbb\xbf\xef\xbb\xbf"Aggregated: Agent Versions: Name",' \
                         b'"Aggregated: Agent Versions: Name","Aggregated: Agent Versions: Version",' \
                         b'"Aggregated: Agent Versions: Status"\r\n"","Cylance Agent","2.0.1490",""\r\n'
