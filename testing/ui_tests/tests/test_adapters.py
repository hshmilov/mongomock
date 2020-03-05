import pytest
from flaky import flaky
from selenium.common.exceptions import NoSuchElementException

from axonius.consts.gui_consts import DISTINCT_ADAPTERS_COUNT_FIELD, ADAPTER_CONNECTIONS_FIELD
from axonius.utils.parsing import normalize_adapter_device, NORMALIZED_HOSTNAME, \
    ips_do_not_contradict_or_mac_intersection
from axonius.consts.plugin_consts import PLUGIN_NAME
from services.adapters.carbonblack_defense_service import CarbonblackDefenseService
from services.adapters.csv_service import CsvService
from services.adapters.esx_service import EsxService
from services.adapters.nexpose_service import NexposeService
from test_credentials.test_esx_credentials import client_details as esx_client_details
from test_credentials.test_carbonblack_defense_credentials import client_details as carbonblack_defence_client_details
from test_credentials.test_nexpose_credentials import client_details as nexpose_client_details
from test_credentials.test_csv_credentials import \
    client_details as csv_client_details, USERS_CLIENT_FILES
from ui_tests.tests.ui_test_base import TestBase

AD_NAME = 'Microsoft Active Directory (AD)'
CSV_ADAPTER_QUERY = 'adapters_data.csv_adapter.id == exists(true)'
CSV_FILE_NAME = 'file_path'  # Changed by Alex A on Jan 27 2020 - because schema changed
CSV_INPUT_ID = 'file_path'  # Changed by Alex A on Jan 27 2020 - because schema changed
CSV_NAME = 'CSV Serials'
JSON_NAME = 'JSON File'
CSV_PLUGIN_NAME = 'csv_adapter'
QUERY_WIZARD_CSV_DATE_PICKER_VALUE = '2020-01-02 02:13:24.485Z'
EXPECTED_ADAPTER_LIST_LABELS = [
    'CSV Serials - users_1',
    'CSV Serials - users_2',
    'CSV Serials - users_3',
    'JSON File - JSON File'
]


ESX_NAME = 'VMware ESXi'
CARBONBLACKDEFENCE_NAME = 'Carbon Black CB Defense'
CARBONBLACKDEFENCE_PLUGIN_NAME = 'carbonblack_defense_adapter'
ESX_PLUGIN_NAME = 'esx_adapter'

NEXPOSE_NAME = 'Rapid7 Nexpose'
NEXPOSE_PLUGIN_NAME = 'nexpose_adapter'


class TestAdapters(TestBase):
    # Sometimes upload file to CSV adapter does not work
    @flaky(max_runs=2)
    def test_upload_csv_file(self):
        try:
            with CsvService().contextmanager(take_ownership=True):
                self._upload_csv(CSV_FILE_NAME, csv_client_details)
                self.base_page.run_discovery()
                self.devices_page.switch_to_page()
                self.devices_page.fill_filter(CSV_ADAPTER_QUERY)
                self.devices_page.enter_search()
                self.devices_page.wait_for_table_to_load()
                assert self.devices_page.count_entities() > 0
                self.adapters_page.switch_to_page()
                self.adapters_page.clean_adapter_servers(CSV_NAME, True)
        finally:
            self.adapters_page.clean_adapter_servers(CSV_NAME)
            self.wait_for_adapter_down(CSV_PLUGIN_NAME)

    # Sometimes upload file to CSV adapter does not work
    @flaky(max_runs=2)
    def test_query_wizard_include_outdated_adapter_devices(self):
        try:
            with CsvService().contextmanager(take_ownership=True):
                self._upload_csv(CSV_FILE_NAME, csv_client_details)
                self.base_page.run_discovery()
                self.devices_page.switch_to_page()
                self.devices_page.click_query_wizard()
                self.devices_page.select_query_adapter(CSV_NAME)
                self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN)
                self.devices_page.select_query_comp_op('<')
                self.devices_page.fill_query_wizard_date_picker(QUERY_WIZARD_CSV_DATE_PICKER_VALUE)
                self.devices_page.close_datepicker()
                self.devices_page.click_search()
                self.devices_page.wait_for_table_to_load()
                assert self.devices_page.count_entities() == 1
                self.devices_page.click_query_wizard()
                self.devices_page.click_wizard_outdated_toggle()
                self.devices_page.click_search()
                self.devices_page.wait_for_table_to_load()
                assert self.devices_page.count_entities() == 2
                self.adapters_page.switch_to_page()
                self.adapters_page.clean_adapter_servers(CSV_NAME, True)
        finally:
            self.adapters_page.clean_adapter_servers(CSV_NAME)
            self.wait_for_adapter_down(CSV_PLUGIN_NAME)

    def test_esx_nexpose_correlation(self):
        try:
            esx_adapter = EsxService()
            nexpose_adapter = NexposeService()
            with esx_adapter.contextmanager(take_ownership=True):
                with nexpose_adapter.contextmanager(take_ownership=True):
                    # Raise a system with esx + nexpose
                    self.adapters_page.wait_for_adapter(ESX_NAME)
                    # Sometimes this page is flaky
                    self.adapters_page.click_adapter(ESX_NAME)
                    self.adapters_page.wait_for_spinner_to_end()
                    self.adapters_page.wait_for_table_to_load()
                    self.adapters_page.click_new_server()
                    self.adapters_page.fill_creds(**esx_client_details[0][0])
                    self.adapters_page.click_save()
                    self.adapters_page.wait_for_spinner_to_end()

                    self.adapters_page.switch_to_page()
                    self.adapters_page.wait_for_adapter(NEXPOSE_NAME)
                    self.adapters_page.click_adapter(NEXPOSE_NAME)
                    self.adapters_page.wait_for_spinner_to_end()
                    self.adapters_page.wait_for_table_to_load()
                    self.adapters_page.click_new_server()
                    self.adapters_page.fill_creds(**nexpose_client_details)
                    self.adapters_page.click_save()

                    # Activate discovery phase
                    self.base_page.run_discovery()

                    # Expected result:
                    # 1. There are devices correlated between esx and nexpose
                    query = '(adapters_data.esx_adapter.id == ({"$exists":true,"$ne": ""})) and ' \
                            '(adapters_data.nexpose_adapter.id == ({"$exists":true,"$ne": ""}))'
                    self.devices_page.switch_to_page()
                    self.devices_page.run_filter_query(query)
                    assert self.devices_page.count_entities() > 0

                    # Take one device that has both adapters
                    # Check if they really have the same hostname or MAC
                    internal_axon_id = self.devices_page.click_row()
                    device = self.axonius_system.get_devices_db().find_one({
                        'internal_axon_id': internal_axon_id
                    })
                    adapters = device['adapters']
                    assert len(adapters) >= 2
                    esx_adapter_from_device = next((x for x in adapters if x[PLUGIN_NAME] == ESX_PLUGIN_NAME), None)
                    nexpose_adapter_from_device = next((x for x in adapters if x[PLUGIN_NAME] == NEXPOSE_PLUGIN_NAME),
                                                       None)
                    assert esx_adapter_from_device
                    assert nexpose_adapter_from_device
                    normalize_adapter_device(nexpose_adapter_from_device)
                    normalize_adapter_device(esx_adapter_from_device)

                    # either hostname equals
                    hostname_equals = (nexpose_adapter_from_device['data'].get(NORMALIZED_HOSTNAME) and
                                       nexpose_adapter_from_device['data'].get(NORMALIZED_HOSTNAME) ==
                                       esx_adapter_from_device['data'].get(NORMALIZED_HOSTNAME))

                    #  and no ip contradiction
                    mac_equals_ip_no_contradict = ips_do_not_contradict_or_mac_intersection(nexpose_adapter_from_device,
                                                                                            esx_adapter_from_device)

                    assert hostname_equals or mac_equals_ip_no_contradict

        finally:
            self.adapters_page.switch_to_page()
            self.adapters_page.clean_adapter_servers(ESX_NAME)
            self.adapters_page.clean_adapter_servers(NEXPOSE_NAME)
            self.wait_for_adapter_down(ESX_PLUGIN_NAME)
            self.wait_for_adapter_down(NEXPOSE_PLUGIN_NAME)

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
                self._upload_csv(list(client.keys())[0], client, True)
                self.adapters_page.wait_for_server_green(position)
            self.adapters_page.switch_to_page()
            self._open_add_edit_server(JSON_NAME, 1)
            self.adapters_page.fill_creds(connectionLabel=JSON_NAME)
            self.adapters_page.click_save()
            self.adapters_page.wait_for_server_green(1)
            self.check_for_connection_labels()
            # restart the adapter and check again
            # https://axonius.atlassian.net/browse/AX-6191
            service.stop()
            service.start_and_wait()
            self.adapters_page.switch_to_page()
            self._open_add_edit_server(CSV_NAME, 1)
            self.adapters_page.click_save()
            self.check_for_connection_labels()
            self.adapters_page.clean_adapter_servers(CSV_NAME, True)
            self.wait_for_adapter_down(CSV_PLUGIN_NAME)

    def check_for_connection_labels(self):
        self.base_page.run_discovery()
        self.users_page.switch_to_page()
        self.users_page.run_filter_query('avidor')
        self.users_page.hover_over_entity_adapter_icon(index=0)
        data = self.users_page.get_adapters_popup_table_data()
        names = [item['Name'] for item in data]
        all_is_good = True
        for name in EXPECTED_ADAPTER_LIST_LABELS:
            if name not in names:
                all_is_good = False

        assert all_is_good

    def _upload_csv(self, csv_file_name, csv_data, is_user_file=False):
        self._open_add_edit_server(CSV_NAME)
        self.adapters_page.upload_file_by_id(CSV_INPUT_ID, csv_data[csv_file_name].file_contents)
        self.adapters_page.fill_creds(user_id=csv_file_name, connectionLabel=csv_file_name)
        if is_user_file:
            self.adapters_page.find_checkbox_by_label('File contains users information').click()
        self.adapters_page.click_save()

    def _open_add_edit_server(self, adapter_name, row_position=0):
        self.adapters_page.wait_for_adapter(adapter_name)
        self.adapters_page.click_adapter(adapter_name)
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.wait_for_table_to_load()
        if row_position == 0:
            self.adapters_page.click_new_server()
        else:
            self.adapters_page.click_edit_server(row_position - 1)

    def test_adapters_count(self):
        self.adapters_page.switch_to_page()
        service = CarbonblackDefenseService()
        try:
            with service.contextmanager(take_ownership=True):
                self.adapters_page.wait_for_adapter(CARBONBLACKDEFENCE_NAME)
                self.adapters_page.click_adapter(CARBONBLACKDEFENCE_NAME)
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.wait_for_table_to_load()
                self.adapters_page.click_new_server()
                self.adapters_page.fill_creds(**carbonblack_defence_client_details)
                self.adapters_page.click_save()
                self.adapters_page.wait_for_spinner_to_end()

                self.base_page.run_discovery()

                query = '((adapters_data.carbonblack_defense_adapter.adapter_count == ({"$exists":true,"$ne":null})))'
                self.devices_page.switch_to_page()
                self.devices_page.run_filter_query(query)
                assert self.devices_page.count_entities() > 0
                query = '(adapters_data.carbonblack_defense_adapter.adapter_count > 1)'
                self.devices_page.run_filter_query(query)
                assert self.devices_page.count_entities() > 0
                query = '(adapters_data.carbonblack_defense_adapter.adapter_count > 10)'
                self.devices_page.run_filter_query(query)
                assert self.devices_page.count_entities() == 0
        finally:
            self.adapters_page.switch_to_page()
            self.adapters_page.clean_adapter_servers(CARBONBLACKDEFENCE_NAME, True)

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
        with pytest.raises(NoSuchElementException) as exception_info:
            self.devices_page.select_custom_data_field(ADAPTER_CONNECTIONS_FIELD)
        assert exception_info.match('Message: no such element:.*')
