import pytest
from selenium.common.exceptions import NoSuchElementException

from services.adapters.aws_service import AwsService
from services.adapters import stresstest_service
from services.plugins.general_info_service import GeneralInfoService
from ui_tests.tests.test_entities_table import TestEntitiesTable
from ui_tests.tests.ui_consts import (MANAGED_DEVICES_QUERY_NAME,
                                      STRESSTEST_ADAPTER,
                                      STRESSTEST_ADAPTER_NAME,
                                      AD_ADAPTER_NAME, AWS_ADAPTER_NAME, AWS_ADAPTER)

from test_credentials.test_crowd_strike_mock_credentials import crowd_strike_json_file_mock_devices
from test_credentials.test_aws_credentials import client_details


class TestDevicesTable(TestEntitiesTable):
    QUERY_FILTER_DEVICES = 'specific_data.data.hostname == regex("w", "i")'
    TARGET_HOSTNAME = '22AD'

    def test_devices_export_csv(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()

        self.devices_page.wait_for_csv_to_update_cache()

        # filter the ui to fit the QUERY_FILTER_DEVICES of the csv
        self.devices_page.query_hostname_contains('w')

        result = self.devices_page.generate_csv('devices',
                                                self.QUERY_FIELDS,
                                                self.QUERY_FILTER_DEVICES)
        self.devices_page.assert_csv_match_ui_data(result)

    def test_device_table_field_export(self):
        self.enforcements_page.switch_to_page()
        with GeneralInfoService().contextmanager(take_ownership=True):
            self.enforcements_page.create_run_wmi_scan_on_each_cycle_enforcement()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.click_query_wizard()
            self.devices_page.select_query_field(self.devices_page.FIELD_USERS_USERNAME)
            self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS)
            self.devices_page.click_search()
            self.devices_page.wait_for_table_to_load()
            self.devices_page.click_row()
            self.devices_page.wait_for_spinner_to_end()
            self.devices_page.click_general_tab()

            # Test export csv of Network Interfaces
            self.devices_page.click_tab(self.devices_page.FIELD_NETWORK_INTERFACES)
            self.devices_page.assert_csv_field_match_ui_data(self.devices_page.generate_csv_field(
                'devices',
                self.driver.current_url.split('/')[-1],
                self.devices_page.FIELD_NETWORK_INTERFACES_NAME,
                self.devices_page.FIELD_MAC_NAME
            ))
            # Test with sort of 'array' field
            self.devices_page.click_sort_column(self.devices_page.FIELD_IPS)
            self.devices_page.assert_csv_field_match_ui_data(self.devices_page.generate_csv_field(
                'devices',
                self.driver.current_url.split('/')[-1],
                self.devices_page.FIELD_NETWORK_INTERFACES_NAME,
                self.devices_page.FIELD_IPS_NAME,
                desc=True
            ))

            # Test export csv of Users
            self.devices_page.click_tab(self.devices_page.FIELD_USERS)
            self.devices_page.assert_csv_field_match_ui_data(self.devices_page.generate_csv_field(
                'devices',
                self.driver.current_url.split('/')[-1],
                self.devices_page.FIELD_USERS_NAME,
                self.devices_page.FIELD_SID_NAME
            ))
            # Test with sort of 'datetime' field
            self.devices_page.click_sort_column(self.devices_page.FIELD_USERS_LAST_USE)
            self.devices_page.assert_csv_field_match_ui_data(self.devices_page.generate_csv_field(
                'devices',
                self.driver.current_url.split('/')[-1],
                self.devices_page.FIELD_USERS_NAME,
                self.devices_page.FIELD_USERS_LAST_USE_NAME,
                desc=True
            ))
            # Test with sort of 'bool' field
            self.devices_page.click_sort_column(self.devices_page.FIELD_USERS_LOCAL)
            self.devices_page.assert_csv_field_match_ui_data(self.devices_page.generate_csv_field(
                'devices',
                self.driver.current_url.split('/')[-1],
                self.devices_page.FIELD_USERS_NAME,
                self.devices_page.FIELD_USERS_LOCAL_NAME,
                desc=True
            ))

    def test_device_table_field(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.query_json_adapter()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row()
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.click_general_tab()

        # Test merged rows of Network Interfaces
        self.devices_page.click_tab(self.devices_page.FIELD_NETWORK_INTERFACES)
        assert int(self.devices_page.get_raw_count_entities()[1:-1]) == 2
        field_data = self.devices_page.get_field_table_data()
        assert ['06:3A:9B:D7:D7:A8', '10.0.2.1\n10.0.2.2', '10.0.2.0/24', 'vlan0\nvlan1', '1\n2'] == field_data[0]
        assert ['06:3A:9B:D7:D7:A8', '10.0.2.3', '', 'vlan0\nvlan1', '1\n2'] == field_data[1]

        self.devices_page.switch_to_page()
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.clear_filter()
        self.devices_page.query_printer_device()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row()
        self.devices_page.click_general_tab()
        # there should be no network interface tab
        with pytest.raises(NoSuchElementException):
            self.devices_page.click_tab(self.devices_page.FIELD_NETWORK_INTERFACES)

    def test_select_all_devices(self):
        with AwsService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(AWS_ADAPTER_NAME)
            client_details[1][0].pop('get_all_regions', None)
            self.adapters_page.add_server(client_details[1][0], AWS_ADAPTER_NAME)
            self.base_page.run_discovery(wait=True)
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_load()
            self.devices_page.toggle_select_all_rows_checkbox()

            assert self.devices_page.count_entities() > self.devices_page.count_selected_entities()
            self.devices_page.click_select_all_entities()
            assert self.devices_page.count_entities() == self.devices_page.count_selected_entities()
            self.adapters_page.clean_adapter_servers(AWS_ADAPTER_NAME, delete_associated_entities=True)
        self.wait_for_adapter_down(AWS_ADAPTER)

    def test_select_devices(self):
        stress = stresstest_service.StresstestService()

        with stress.contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(STRESSTEST_ADAPTER_NAME)
            device_dict = {'device_count': 2500, 'name': 'testonius'}
            self.adapters_page.add_server(device_dict, STRESSTEST_ADAPTER_NAME)
            self.adapters_page.wait_for_server_green()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_load()
            assert self.devices_page.find_active_page_number() == '1'
            self.devices_page.select_page_size(20)
            self.devices_page.toggle_select_all_rows_checkbox()
            self.devices_page.select_page_size(50)
            assert self.devices_page.count_selected_entities() == 20
            self.devices_page.toggle_select_all_rows_checkbox()
            assert self.devices_page.verify_no_entities_selected()
            self.devices_page.toggle_select_all_rows_checkbox()
            assert self.devices_page.count_selected_entities() == 50
            self.devices_page.select_pagination_index(4)
            assert self.devices_page.find_active_page_number() == '2'
            self.devices_page.toggle_select_all_rows_checkbox()
            assert self.devices_page.count_selected_entities() == 100
            self.devices_page.select_pagination_index(5)
            assert self.devices_page.find_active_page_number() == '3'
            self.devices_page.click_row_checkbox(1)
            self.devices_page.click_row_checkbox(3)
            self.devices_page.click_row_checkbox(7)
            self.devices_page.select_pagination_index(11)
            self.devices_page.wait_for_spinner_to_end()
            self.devices_page.toggle_select_all_rows_checkbox()
            assert self.devices_page.count_selected_entities() == 103 + (self.devices_page.count_entities() % 50)
            self.devices_page.click_select_all_entities()
            assert self.devices_page.count_selected_entities() == self.devices_page.count_entities()
            self.devices_page.click_clear_all_entities()
            assert self.devices_page.verify_no_entities_selected()

            # test pagination refresh
            self.devices_page.execute_saved_query(MANAGED_DEVICES_QUERY_NAME)
            assert self.devices_page.find_active_page_number() == '1'

            self.adapters_page.clean_adapter_servers(STRESSTEST_ADAPTER_NAME)
            self.wait_for_adapter_down(STRESSTEST_ADAPTER)

    def test_scroll_reset_on_data_change(self):
        stress = stresstest_service.StresstestService()

        with stress.contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(STRESSTEST_ADAPTER_NAME)
            device_dict = {'device_count': 2500, 'name': 'testonius'}
            self.adapters_page.add_server(device_dict, STRESSTEST_ADAPTER_NAME)
            self.adapters_page.wait_for_server_green()
            self.base_page.run_discovery()

            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_load()
            self.devices_page.select_page_size(50)

            # pagination change
            assert self.devices_page.get_table_scroll_position()[1] == '0'
            self.devices_page.set_table_scroll_position(0, 30)
            assert self.devices_page.get_table_scroll_position()[1] != '0'
            self.devices_page.select_pagination_index(4)  # page 2
            assert self.devices_page.get_table_scroll_position()[1] == '0'

            # filter change
            self.devices_page.set_table_scroll_position(0, 30)
            assert self.devices_page.get_table_scroll_position()[1] != '0'
            self.devices_page.query_hostname_contains('w')
            assert self.devices_page.get_table_scroll_position()[1] == '0'

            self.adapters_page.clean_adapter_servers(STRESSTEST_ADAPTER_NAME)
        self.wait_for_adapter_down(STRESSTEST_ADAPTER)

    def test_device_network_interfaces_csv_search(self):
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row()
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.click_general_tab()
        self.devices_page.click_tab(self.devices_page.FIELD_NETWORK_INTERFACES)

        self.devices_page.assert_csv_field_with_search('')
        self.devices_page.assert_csv_field_with_search('06:80:99:50:D3:5E')
        self.devices_page.assert_csv_field_with_search('search text that will definitely have no results')

    def test_devices_preferred_fields(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        view_data = self.devices_page.get_all_data()
        self.devices_page.edit_columns(add_col_names=self.devices_page.PREFERRED_FIELDS)
        self.devices_page.wait_for_table_to_load()
        assert not self.devices_page.get_all_data() == view_data

    def test_devices_search_reset(self):
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.fill_filter(self.QUERY_FILTER_DEVICES)

        assert self.devices_page.find_search_value() == self.QUERY_FILTER_DEVICES

        self.devices_page.enter_search()
        self.devices_page.reset_query()

        assert self.devices_page.find_search_value() == ''

    def test_device_expand_row(self):
        self.adapters_page.add_json_server(crowd_strike_json_file_mock_devices)
        self.base_page.run_discovery(wait=True)
        self.devices_page.switch_to_page()
        self.devices_page.query_hostname_contains(self.TARGET_HOSTNAME)
        self.devices_page.click_expand_row(index=1)
        # The value from all adapters seperated by \n
        device_host_name = self.devices_page.get_column_data_expand_row(self.devices_page.FIELD_HOSTNAME_TITLE)
        # Make sure all values are not ''
        assert device_host_name and all(x != '' for x in device_host_name[0].split('\n'))
        assert self.devices_page.NAME_ADAPTERS_AD in self.devices_page.get_column_data_adapter_names()
        assert self.devices_page.NAME_ADAPTERS_JSON in self.devices_page.get_column_data_adapter_names()
        self.devices_page.edit_columns(add_col_names=[self.devices_page.FIELD_HOSTNAME_TITLE],
                                       remove_col_names=[self.devices_page.FIELD_HOSTNAME_TITLE],
                                       adapter_title=[AD_ADAPTER_NAME])
        assert device_host_name != self.devices_page.get_column_data_expand_row(
            self.devices_page.FIELD_HOSTNAME_TITLE
        )
        self.adapters_page.remove_json_extra_server(crowd_strike_json_file_mock_devices)
