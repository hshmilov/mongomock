import pytest

from axonius.consts.gui_consts import DISTINCT_ADAPTERS_COUNT_FIELD, ADAPTER_CONNECTIONS_FIELD
from axonius.utils.parsing import normalize_adapter_device, NORMALIZED_HOSTNAME, \
    ips_do_not_contradict_or_mac_intersection
from axonius.consts.plugin_consts import PLUGIN_NAME
from services.adapters.carbonblack_defense_service import CarbonblackDefenseService
from services.adapters.csv_service import CsvService
import test_credentials.json_file_credentials
from test_credentials.test_carbonblack_defense_credentials import client_details as carbonblack_defence_client_details
from test_credentials.test_csv_credentials import \
    client_details as csv_client_details, USERS_CLIENT_FILES
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import CSV_PLUGIN_NAME, CSV_NAME, JSON_ADAPTER_PLUGIN_NAME
from testing.test_credentials.test_csv_credentials import CSV_FIELDS
from test_helpers.file_mock_credentials import FileForCredentialsMock

AD_NAME = 'Microsoft Active Directory (AD)'
JSON_NAME = 'JSON File'
QUERY_WIZARD_CSV_DATE_PICKER_VALUE = '2020-01-02 02:13:24.485Z'
EXPECTED_ADAPTER_LIST_LABELS = [
    'CSV - users_1',
    'CSV - users_2',
    'CSV - users_3',
    'JSON File - JSON File'
]

ESX_NAME = 'VMware ESXi'
CARBONBLACKDEFENCE_NAME = 'Carbon Black CB Defense'
CARBONBLACKDEFENCE_PLUGIN_NAME = 'carbonblack_defense_adapter'
ESX_PLUGIN_NAME = 'esx_adapter'

NEXPOSE_NAME = 'Rapid7 Nexpose'
NEXPOSE_PLUGIN_NAME = 'nexpose_adapter'

LAST_SEEN_THRESHOLD_HOURS = '21600'

# pylint: disable= too-many-statements


class TestAdapters(TestBase):
    # Sometimes upload file to CSV adapter does not work
    def test_upload_csv_file(self):
        with CsvService().contextmanager(take_ownership=True):
            self.adapters_page.upload_csv(self.adapters_page.CSV_FILE_NAME, csv_client_details)
            self.adapters_page.wait_for_data_collection_toaster_start()
            self.adapters_page.wait_for_data_collection_toaster_absent()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.fill_filter(self.adapters_page.CSV_ADAPTER_QUERY)
            self.devices_page.enter_search()
            self.devices_page.wait_for_table_to_load()
            assert self.devices_page.count_entities() > 0
            self.adapters_page.switch_to_page()
            self.adapters_page.clean_adapter_servers(CSV_NAME)
        self.wait_for_adapter_down(CSV_PLUGIN_NAME)

    def test_json_csv_correlation(self):
        csv_adapter = CsvService()
        with csv_adapter.contextmanager(take_ownership=True):

            self.adapters_page.switch_to_page()
            self.adapters_page.wait_for_adapter(CSV_NAME)

            mac_address = test_credentials.json_file_credentials.DEVICE_MAC
            ip_address = test_credentials.json_file_credentials.DEVICE_FIRST_IP
            hostname = test_credentials.json_file_credentials.DEVICE_FIRST_HOSTNAME
            client_details = {
                'user_id': 'user',
                # an array of char
                'file_path': FileForCredentialsMock(
                    'file_path',
                    ','.join(CSV_FIELDS) +
                    f'\n{hostname},Serial2,Windows,{mac_address},Office,2020-04-01 02:13:24.485Z, {ip_address}'
                    '\nJames,Serial3,Linux,11:22:22:33:11:33,Office,2020-01-01 02:13:24.485Z')
            }
            self.adapters_page.upload_csv(self.adapters_page.CSV_FILE_NAME, client_details)
            self.adapters_page.wait_for_data_collection_toaster_start()
            self.adapters_page.wait_for_data_collection_toaster_absent()

            self.adapters_page.switch_to_page()
            # Activate discovery phase
            self.base_page.run_discovery()
            print('Finished discovery.')

            # Expected result:
            # 1. There are devices correlated between json file and csv
            query = '(adapters_data.json_file_adapter.id == ({"$exists":true,"$ne": ""})) and ' \
                    '(adapters_data.csv_adapter.id == ({"$exists":true,"$ne": ""}))'
            self.devices_page.switch_to_page()
            self.devices_page.run_filter_query(query)
            assert self.devices_page.count_entities() > 0
            print('Filtered json and csv devices.')

            # Take one device that has both adapters
            # Check if they really have the same hostname or MAC
            internal_axon_id = self.devices_page.click_row()
            device = self.axonius_system.get_devices_db().find_one({
                'internal_axon_id': internal_axon_id
            })
            adapters = device['adapters']
            assert len(adapters) >= 2
            csv_adapter_from_device = next((x for x in adapters if x[PLUGIN_NAME] == CSV_PLUGIN_NAME), None)
            json_adapter_from_device = next((x for x in adapters if x[PLUGIN_NAME] == JSON_ADAPTER_PLUGIN_NAME),
                                            None)
            print('Got a json and a csv device.')

            assert csv_adapter_from_device
            assert json_adapter_from_device
            normalize_adapter_device(csv_adapter_from_device)
            normalize_adapter_device(json_adapter_from_device)

            # either hostname equals
            hostname_equals = (csv_adapter_from_device['data'].get(NORMALIZED_HOSTNAME) and
                               csv_adapter_from_device['data'].get(NORMALIZED_HOSTNAME) ==
                               json_adapter_from_device['data'].get(NORMALIZED_HOSTNAME))

            #  and no ip contradiction
            mac_equals_ip_no_contradict = ips_do_not_contradict_or_mac_intersection(csv_adapter_from_device,
                                                                                    json_adapter_from_device)

            print('Got hostname or mac ip contradiction.')
            assert hostname_equals or mac_equals_ip_no_contradict

            self.adapters_page.switch_to_page()
            self.adapters_page.clean_adapter_servers(CSV_NAME)
            print('Cleaned csv clients.')
        self.wait_for_adapter_down(CSV_PLUGIN_NAME)

    @pytest.mark.skip('AX-7517')
    def test_adapter_clients_label(self):
        """
        this test check for the connection label ( defined in the client configuration of the adapter ) existence
        upload 3 csv files and define a connection label to json_file adapter, check after correlation we have one user
        with all 4 labels at the right place
        :return:
        """
        service = CsvService()
        with service.contextmanager(take_ownership=True):
            for position, client in enumerate(USERS_CLIENT_FILES, start=1):
                self.adapters_page.upload_csv(list(client.keys())[0], client, True)
                self.adapters_page.wait_for_server_green(position)
            self.adapters_page.switch_to_page()
            self.adapters_page.open_add_edit_server(JSON_NAME, 1)
            self.adapters_page.fill_creds(connectionLabel=JSON_NAME)
            self.adapters_page.click_save()
            self.adapters_page.wait_for_server_green(1)
            self.adapters_page.refresh()
            self.adapters_page.click_adapter(JSON_NAME)
            self.adapters_page.wait_for_table_to_be_responsive()
            assert self.adapters_page.get_column_data_inline('Connection Label')[0] == JSON_NAME
            self.adapters_page.click_edit_server()
            assert self.adapters_page.find_server_connection_label_value() == JSON_NAME
            self.adapters_page.click_cancel()

            self.check_for_connection_labels()
            # restart the adapter and check again
            # https://axonius.atlassian.net/browse/AX-6191
            service.stop()
            service.start_and_wait()
            self.adapters_page.switch_to_page()
            self.adapters_page.open_add_edit_server(CSV_NAME, 1)
            self.adapters_page.click_save()
            self.check_for_connection_labels()
            self.adapters_page.clean_adapter_servers(CSV_NAME, True)
        self.wait_for_adapter_down(CSV_PLUGIN_NAME)

    def check_for_connection_labels(self):
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        self.users_page.refresh()
        self.users_page.wait_for_table_to_be_responsive()
        self.users_page.run_filter_query('avidor')
        self.users_page.hover_over_entity_adapter_icon(index=0)
        data = self.users_page.get_adapters_popup_table_data()
        names = [item['Name'] for item in data]
        all_is_good = True
        for name in EXPECTED_ADAPTER_LIST_LABELS:
            if name not in names:
                all_is_good = False

        assert all_is_good

    def test_adapters_count(self):
        self.adapters_page.switch_to_page()
        service = CarbonblackDefenseService()
        with service.contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(CARBONBLACKDEFENCE_NAME)
            self.adapters_page.click_adapter(CARBONBLACKDEFENCE_NAME)
            self.adapters_page.wait_for_spinner_to_end()
            self.adapters_page.wait_for_table_to_load()
            self.adapters_page.click_new_server()
            self.adapters_page.fill_creds(**carbonblack_defence_client_details)
            self.adapters_page.click_save()
            self.adapters_page.click_advanced_settings()
            self.adapters_page.fill_last_seen_threshold_hours(LAST_SEEN_THRESHOLD_HOURS)
            self.adapters_page.save_advanced_settings()
            self.adapters_page.wait_for_spinner_to_end()

            self.base_page.run_discovery()

            query = '((adapters_data.carbonblack_defense_adapter.adapter_count == ({"$exists":true,"$ne":null})))'
            self.devices_page.switch_to_page()
            self.devices_page.run_filter_query(query)
            assert self.devices_page.count_entities() > 0
            query = '(adapters_data.carbonblack_defense_adapter.adapter_count > 1)'
            self.devices_page.run_filter_query(query)
            assert self.devices_page.count_entities() > 0
            query = '(adapters_data.carbonblack_defense_adapter.adapter_count > 50)'
            self.devices_page.run_filter_query(query)
            assert self.devices_page.count_entities() == 0
            self.adapters_page.switch_to_page()
            self.adapters_page.clean_adapter_servers(CARBONBLACKDEFENCE_NAME, True)

        self.wait_for_adapter_down(CARBONBLACKDEFENCE_PLUGIN_NAME)

    def test_query_wizard_dynamic_and_blacklist_fields(self):
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        self.devices_page.select_query_adapter(AD_NAME)
        self.devices_page.select_query_field(DISTINCT_ADAPTERS_COUNT_FIELD)
        self.devices_page.click_search()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() > 0
        self.devices_page.reset_query()
        self.devices_page.click_query_wizard()
        self.devices_page.select_query_field(DISTINCT_ADAPTERS_COUNT_FIELD)
        self.devices_page.click_search()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() > 0
        # Index error means there were no elements found (Changed because of #5320)
        with pytest.raises(IndexError) as exception_info:
            self.devices_page.select_custom_data_field(ADAPTER_CONNECTIONS_FIELD)
        assert exception_info.match('list index out of range')
