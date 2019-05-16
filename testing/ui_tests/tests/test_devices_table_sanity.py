from ui_tests.tests.test_entities_table import TestEntitiesTable
from services.adapters.aws_service import AwsService
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
