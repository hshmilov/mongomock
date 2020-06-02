import pytest

from services.plugins.general_info_service import GeneralInfoService
from ui_tests.tests.test_entities_table import TestEntitiesTable
from ui_tests.tests.ui_consts import AD_MISSING_AGENTS_QUERY_NAME, WMI_INFO_ADAPTER


class TestDevicesTableMoreCases(TestEntitiesTable):
    QUERY_FILTER_LAST_SEEN = '(specific_data.data.last_seen >= date("NOW - 7d"))'

    @pytest.mark.skip('ad change')
    def test_devices_last_seen_export_csv(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()

        self.devices_page.wait_for_csv_to_update_cache()

        # filter the ui to fit the QUERY_FILTER_DEVICES of the csv
        self.devices_page.add_query_last_seen_in_days(7)

        result = self.devices_page.generate_csv('devices',
                                                self.QUERY_FIELDS,
                                                self.QUERY_FILTER_LAST_SEEN)
        self.devices_page.assert_csv_match_ui_data(result)

    def test_export_csv_progress_icon(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_spinner_to_end()

        self.devices_page.click_export_csv()
        self.devices_page.wait_for_csv_loading_absent()
        assert not self.devices_page.find_table_options_open()

    @pytest.mark.skip('ad change')
    def test_devices_save_query(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()

        self.devices_page.customize_view_and_save('test_save_query', 50, self.devices_page.FIELD_HOSTNAME_TITLE,
                                                  [],
                                                  [self.devices_page.FIELD_LAST_SEEN, self.devices_page.FIELD_OS_TYPE],
                                                  self.devices_page.JSON_ADAPTER_FILTER)
        view_data = self.devices_page.get_all_data()

        # Load some default view, to change it and test the saved view's influence
        self.devices_page.execute_saved_query(AD_MISSING_AGENTS_QUERY_NAME)
        assert self.devices_page.get_all_data() != view_data

        self.devices_page.clear_filter()
        self.devices_page.execute_saved_query('test_save_query')

        # Check loaded data is equal to original one whose view was saved
        assert self.devices_page.get_all_data() == view_data

    @pytest.mark.skip('ad change')
    def test_wmi_info_shown(self):
        self.enforcements_page.switch_to_page()
        with GeneralInfoService().contextmanager(take_ownership=True):
            self.enforcements_page.create_run_wmi_scan_on_each_cycle_enforcement()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.click_query_wizard()
            adapters = self.devices_page.get_query_adapters_list()
            # WMI Info should be in the adapters list because its does have a client
            assert WMI_INFO_ADAPTER in adapters

    def test_devices_delete(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()

        self.devices_page.delete_devices(self.devices_page.JSON_ADAPTER_FILTER)

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
