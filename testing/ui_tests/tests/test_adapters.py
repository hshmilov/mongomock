from flaky import flaky

from axonius.utils.parsing import normalize_adapter_device, NORMALIZED_HOSTNAME, \
    ips_do_not_contradict_or_mac_intersection
from axonius.consts.plugin_consts import PLUGIN_NAME
from services.adapters.csv_service import CsvService
from services.adapters.esx_service import EsxService
from services.adapters.nexpose_service import NexposeService
from test_credentials.test_esx_credentials import client_details as esx_client_details
from test_credentials.test_nexpose_credentials import client_details as nexpose_client_details
from test_credentials.test_csv_credentials import \
    client_details as csv_client_details
from ui_tests.tests.ui_test_base import TestBase

CSV_ADAPTER_QUERY = 'adapters_data.csv_adapter.id == exists(true)'
CSV_FILE_NAME = 'csv'
CSV_NAME = 'CSV Serials'
CSV_PLUGIN_NAME = 'csv_adapter'
QUERY_WIZARD_CSV_DATE_PICKER_VALUE = '2018-12-30 02:13:24.485Z'

ESX_NAME = 'VMware ESXi'
ESX_PLUGIN_NAME = 'esx_adapter'

NEXPOSE_NAME = 'Rapid7 Nexpose'
NEXPOSE_PLUGIN_NAME = 'nexpose_adapter'


class TestAdapters(TestBase):
    # Sometimes upload file to CSV adapter does not work
    @flaky(max_runs=2)
    def test_upload_csv_file(self):
        try:
            with CsvService().contextmanager(take_ownership=True):
                self.adapters_page.wait_for_adapter(CSV_NAME)
                self.adapters_page.click_adapter(CSV_NAME)
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.wait_for_table_to_load()
                self.adapters_page.click_new_server()
                self.adapters_page.upload_file_by_id(CSV_FILE_NAME, csv_client_details[CSV_FILE_NAME].file_contents)
                self.adapters_page.fill_creds(user_id=CSV_FILE_NAME)
                self.adapters_page.click_save()
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
                self.adapters_page.wait_for_adapter(CSV_NAME)
                self.adapters_page.click_adapter(CSV_NAME)
                self.adapters_page.wait_for_spinner_to_end()
                self.adapters_page.wait_for_table_to_load()
                self.adapters_page.click_new_server()
                self.adapters_page.upload_file_by_id(CSV_FILE_NAME, csv_client_details[CSV_FILE_NAME].file_contents)
                self.adapters_page.fill_creds(user_id=CSV_FILE_NAME)
                self.adapters_page.click_save()
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
