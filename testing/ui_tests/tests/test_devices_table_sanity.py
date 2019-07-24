from ui_tests.tests.test_entities_table import TestEntitiesTable
from services.adapters.aws_service import AwsService
from services.plugins.general_info_service import GeneralInfoService
from test_credentials.test_aws_credentials import client_details

AWS_NAME = 'Amazon Web Services (AWS)'


class TestDevicesTable(TestEntitiesTable):
    QUERY_FILTER_DEVICES = 'specific_data.data.hostname%20%3D%3D%20regex(%22w%22%2C%20%22i%22)'
    QUERY_FIELDS = 'adapters,specific_data.data.hostname,specific_data.data.name,specific_data.data.last_seen,' \
                   'specific_data.data.os.type,specific_data.data.network_interfaces.ips,' \
                   'specific_data.data.network_interfaces.mac,labels'

    def test_devices_save_query(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()

        self.devices_page.customize_view_and_save('test_save_query', 50, self.devices_page.FIELD_HOSTNAME_TITLE,
                                                  [self.devices_page.FIELD_LAST_SEEN, self.devices_page.FIELD_OS_TYPE],
                                                  self.devices_page.JSON_ADAPTER_FILTER)
        view_data = self.devices_page.get_all_data()

        # Load some default view, to change it and test the saved view's influence
        self.devices_page.execute_saved_query('Windows Operating System')
        assert self.devices_page.get_all_data() != view_data

        self.devices_page.clear_filter()
        self.devices_page.execute_saved_query('test_save_query')

        # Check loaded data is equal to original one whose view was saved
        assert self.devices_page.get_all_data() == view_data

    def test_devices_delete(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()

        self.devices_page.delete_devices(self.devices_page.JSON_ADAPTER_FILTER)

    def test_devices_export_csv(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        # filter the ui to fit the QUERY_FILTER_DEVICES of the csv
        self.devices_page.query_hostname_contains('w')

        result = self.devices_page.generate_csv('devices',
                                                self.QUERY_FIELDS,
                                                self.QUERY_FILTER_DEVICES)
        self.devices_page.assert_csv_match_ui_data(result)

    def test_export_csv_progress_icon(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_spinner_to_end()

        self.devices_page.click_export_csv()

        self.devices_page.wait_for_csv_loading_button_to_be_absent()

        assert not self.devices_page.is_export_csv_button_disabled()

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
        field_data = self.devices_page.get_field_table_data()
        assert ['06:3A:9B:D7:D7:A8', '10.0.2.1\n10.0.2.2', '10.0.2.0/24', 'vlan0, vlan1', '1, 2'] == field_data[0]
        assert ['06:3A:9B:D7:D7:A8', '10.0.2.3', '', 'vlan0, vlan1', '1, 2'] == field_data[1]

    def test_select_all_devices(self):
        with AwsService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(AWS_NAME)
            client_details[1][0].pop('get_all_regions', None)
            self.adapters_page.add_server(client_details[1][0], AWS_NAME)
            self.base_page.run_discovery(wait=True)
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_load()
            self.devices_page.select_all_current_page_rows_checkbox()

            assert self.devices_page.count_entities() > self.devices_page.count_selected_entities()
            self.devices_page.click_select_all_entities()
            assert self.devices_page.count_entities() == self.devices_page.count_selected_entities()
            self.adapters_page.clean_adapter_servers(AWS_NAME, delete_associated_entities=True)
