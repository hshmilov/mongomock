import math
from datetime import datetime
import random

import pytest
from dateutil.relativedelta import relativedelta

from axonius.consts.gui_consts import ADAPTER_CONNECTIONS_FIELD
from json_file_adapter.service import DEVICES_DATA, FILE_NAME, USERS_DATA
from services.adapters import stresstest_scanner_service, stresstest_service
from services.adapters.csv_service import CsvService
from test_credentials.test_aws_credentials_mock import aws_json_file_mock_devices
from test_credentials.test_crowd_strike_mock_credentials import crowd_strike_json_file_mock_devices
from test_credentials.test_csv_credentials import CSV_FIELDS
from test_helpers.file_mock_credentials import FileForCredentialsMock
from ui_tests.tests.ui_consts import (AD_ADAPTER_NAME,
                                      LINUX_QUERY_NAME,
                                      STRESSTEST_ADAPTER,
                                      STRESSTEST_SCANNER_ADAPTER,
                                      WINDOWS_QUERY_NAME,
                                      JSON_ADAPTER_NAME, STRESSTEST_ADAPTER_NAME, STRESSTEST_SCANNER_ADAPTER_NAME,
                                      LABEL_CLIENT_WITH_SAME_ID, CSV_NAME, CSV_PLUGIN_NAME)
from ui_tests.tests.ui_test_base import TestBase


class TestDevicesQueryAdvancedMoreCases(TestBase):
    LABEL_CLIENT_WITH_SAME_ID = 'client_with_same_id'

    def test_devices_id_contains_query(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.build_query_field_contains_with_adapter(self.devices_page.ID_FIELD, 'a',
                                                                  AD_ADAPTER_NAME)
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.click_query_wizard()
        assert self.devices_page.get_query_comp_op() == self.devices_page.QUERY_COMP_CONTAINS

    def test_in_adapters_query(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()

        self.devices_page.select_page_size(50)

        all_adapters = set(self.devices_page.get_column_data_inline_with_remainder(ADAPTER_CONNECTIONS_FIELD))
        adapters = random.sample(all_adapters, math.ceil(len(all_adapters) / 2))

        self.devices_page.click_query_wizard()
        self.devices_page.select_query_field(ADAPTER_CONNECTIONS_FIELD)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_IN)
        self.devices_page.fill_query_string_value(','.join(adapters))
        self.devices_page.wait_for_table_to_be_responsive()

        self.devices_page.click_search()

        self.devices_page.select_page_size(50)

        new_adapters = set(self.devices_page.get_column_data_inline_with_remainder(ADAPTER_CONNECTIONS_FIELD))

        assert len([adapter for adapter in new_adapters if adapter.strip() == '']) == 0

        assert set(adapters).issubset(new_adapters)

        for adapters_values in self.devices_page.get_column_cells_data_inline_with_remainder(ADAPTER_CONNECTIONS_FIELD):
            if isinstance(adapters_values, list):
                assert len(set(adapters_values).intersection(set(adapters))) > 0
            else:
                assert adapters_values in adapters

    def test_last_seen_next_days(self):

        def chabchab_in_result():
            self.devices_page.wait_for_table_to_load()
            try:
                return 'ChabChab' in self.devices_page.get_column_data_inline(
                    self.devices_page.FIELD_ASSET_NAME)
            except ValueError:
                query = self.devices_page.find_search_value()
                self.devices_page.refresh()
                self.devices_page.reset_query()
                self.devices_page.fill_filter(query)
                self.devices_page.enter_search()
                self.devices_page.wait_for_table_to_load()
                return 'ChabChab' in self.devices_page.get_column_data_inline(
                    self.devices_page.FIELD_ASSET_NAME)

        def json_query_filter_last_seen_next_days(days_value=0):
            self.devices_page.click_query_wizard()
            self.devices_page.select_query_with_adapter(attribute=self.devices_page.FIELD_LAST_SEEN,
                                                        operator=self.devices_page.QUERY_COMP_NEXT_DAYS,
                                                        value=days_value)
            self.devices_page.wait_for_table_to_be_responsive()
            self.devices_page.click_search()

        future_date = (datetime.utcnow() + relativedelta(years=+10)).strftime('%Y-%m-%d %H:%M:%SZ')
        client_details = {
            FILE_NAME: 'test_last_seen_next_days',
            DEVICES_DATA: FileForCredentialsMock(DEVICES_DATA, '''
               {
                   "devices" : [{
                       "id": "ChabChab",
                       "name": "ChabChab",
                       "hostname": "ChabChab",
                       "last_seen": "''' + future_date + '''",
                       "network_interfaces": [{
                           "mac": "06:3A:9B:D7:D7:CC",
                           "ips": ["172.21.12.12"]
                       }]
                   }],
                   "fields" : ["id", "network_interfaces", "name", "hostname", "last_seen"],
                   "additional_schema" : [],
                   "raw_fields" : []
                       }
               '''),
            USERS_DATA: FileForCredentialsMock(USERS_DATA, '''
                    {
                        "users" : [],
                         "fields" : [],
                         "additional_schema" : [],
                         "raw_fields" : []                      
                    }
                    ''')
        }

        self.adapters_page.add_server(client_details, adapter_name=JSON_ADAPTER_NAME)
        self.adapters_page.wait_for_data_collection_toaster_start()
        self.adapters_page.wait_for_data_collection_toaster_absent()
        self.devices_page.switch_to_page()
        self.devices_page.refresh()
        json_query_filter_last_seen_next_days(1)
        assert chabchab_in_result() is False
        json_query_filter_last_seen_next_days(100)
        assert chabchab_in_result() is False
        json_query_filter_last_seen_next_days(10000)
        assert chabchab_in_result()
        self.adapters_page.remove_json_extra_server(client_details)

    def test_saved_query_field(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, WINDOWS_QUERY_NAME)
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_LINUX, LINUX_QUERY_NAME)
        self.devices_page.click_query_wizard()

        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_query_field(self.devices_page.FIELD_SAVED_QUERY, parent=expressions[0])
        self.devices_page.select_query_value(WINDOWS_QUERY_NAME, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        for os_type in self.devices_page.get_column_data_slicer(self.devices_page.FIELD_OS_TYPE):
            assert os_type == self.devices_page.VALUE_OS_WINDOWS

        self.devices_page.select_query_value(LINUX_QUERY_NAME, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert not len(self.devices_page.get_all_data())

    def test_default_field_query_remains_id(self):
        """
        Verify that when switching to crowd strike adapter in the query wizard,
        If the previous field was ID, that it still remains this ID
        Also make sure that if a different field was selected,
        It will be shown and not the ID.
        """
        self.adapters_page.add_server(crowd_strike_json_file_mock_devices, JSON_ADAPTER_NAME)
        self.adapters_page.wait_for_server_green(position=2)
        self.adapters_page.wait_for_table_to_load()
        self.adapters_page.wait_for_data_collection_toaster_absent()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        self.devices_page.select_query_adapter(AD_ADAPTER_NAME)
        self.devices_page.select_query_field(self.devices_page.ID_FIELD)
        self.devices_page.select_query_adapter(JSON_ADAPTER_NAME)
        assert self.devices_page.get_query_field() == self.users_page.ID_FIELD
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES)
        self.devices_page.select_query_adapter(AD_ADAPTER_NAME)
        assert self.devices_page.get_query_field() == self.devices_page.FIELD_NETWORK_INTERFACES
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN)
        self.devices_page.select_query_adapter(JSON_ADAPTER_NAME)
        assert self.devices_page.get_query_field() == self.devices_page.FIELD_LAST_SEEN
        self.devices_page.close_dropdown()
        self.devices_page.wait_for_table_to_load()
        self.adapters_page.remove_server(ad_client=crowd_strike_json_file_mock_devices, adapter_name=JSON_ADAPTER_NAME,
                                         expected_left=1, delete_associated_entities=True,
                                         adapter_search_field=self.adapters_page.JSON_FILE_SERVER_SEARCH_FIELD)

    def test_in_enum_query(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        with stress.contextmanager(take_ownership=True), \
                stress_scanner.contextmanager(take_ownership=True):
            device_dict = {'device_count': 10, 'name': 'blah'}
            stress.add_client(device_dict)
            stress_scanner.add_client(device_dict)

            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_be_responsive()

            self.devices_page.select_page_size(50)

            all_os_types = set(self.devices_page.
                               get_column_data_inline_with_remainder(self.devices_page.FIELD_OS_TYPE))

            os_types = random.sample(all_os_types, math.ceil(len(all_os_types) / 2))

            self.devices_page.click_query_wizard()
            self.devices_page.select_query_field(self.devices_page.FIELD_OS_TYPE)
            self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_IN)
            self.devices_page.fill_query_string_value(','.join(set(os_types)))
            self.devices_page.wait_for_table_to_be_responsive()

            self.devices_page.click_search()

            new_os_types = set(self.devices_page.get_column_data_inline_with_remainder(
                self.devices_page.FIELD_OS_TYPE))

            assert len([os_type for os_type in new_os_types if os_type.strip() == '']) == 0

            assert set(os_types).issubset(new_os_types)

            for os_types_values in self.devices_page.get_column_cells_data_inline_with_remainder(
                    self.devices_page.FIELD_OS_TYPE):
                if isinstance(os_types_values, list):
                    assert len(set(os_types_values).intersection(set(os_types))) > 0
                else:
                    assert os_types_values in os_types

            self.adapters_page.clean_adapter_servers(STRESSTEST_ADAPTER_NAME)
            self.adapters_page.clean_adapter_servers(STRESSTEST_SCANNER_ADAPTER_NAME)
        self.wait_for_stress_adapter_down(STRESSTEST_ADAPTER)
        self.wait_for_stress_adapter_down(STRESSTEST_SCANNER_ADAPTER)

    @pytest.mark.skip('AX-7287')
    def test_connection_label_query_with_same_client_id(self):
        """
          verify connection label when adapter client have same client_id ( like tanium adapters )
          in order to test this mock aws usign json_file adapter and csv adapter are used
          use case : same label on multiple adapters then remove label from one adapter and compare device count
        """
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
                    f'\nkatooth,Serial1,Windows,11:22:22:33:11:33,Office,02:11:24.485Z 02:11:24.485Z, 1.1.1.1')
            }
            self.adapters_page.upload_csv(LABEL_CLIENT_WITH_SAME_ID, client_details)

            devices_by_label = self.devices_page.get_device_count_by_connection_label(
                operator=self.devices_page.QUERY_COMP_EQUALS, value=LABEL_CLIENT_WITH_SAME_ID)

            # update label for csv mock
            self.adapters_page.update_csv_connection_label(file_name=LABEL_CLIENT_WITH_SAME_ID,
                                                           update_label='UPDATE_LABEL')

            update_devices_by_label = self.devices_page.get_device_count_by_connection_label(
                operator=self.devices_page.QUERY_COMP_EQUALS, value=LABEL_CLIENT_WITH_SAME_ID)
            assert update_devices_by_label < devices_by_label

            # update label for aws json file
            self.adapters_page.update_json_file_server_connection_label(client_name=LABEL_CLIENT_WITH_SAME_ID,
                                                                        update_label='UPDATE_LABEL')

            update_devices_by_label = self.devices_page.get_device_count_by_connection_label(
                operator=self.devices_page.QUERY_COMP_EQUALS, value='UPDATE_LABEL')
            assert update_devices_by_label == devices_by_label

            self.adapters_page.clean_adapter_servers(CSV_NAME, True)

        self.wait_for_adapter_down(CSV_PLUGIN_NAME)
        self.adapters_page.remove_json_extra_server(aws_json_mock_with_label)
