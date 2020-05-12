import math
from datetime import datetime
import random

import pytest
from dateutil.relativedelta import relativedelta

from axonius.consts.gui_consts import ADAPTER_CONNECTIONS_FIELD
from json_file_adapter.service import DEVICES_DATA, FILE_NAME, USERS_DATA
from services.adapters import stresstest_scanner_service, stresstest_service
from services.adapters.crowd_strike_service import CrowdStrikeService
from services.adapters.tanium_asset_service import TaniumAssetService
from services.adapters.tanium_discover_service import TaniumDiscoverService
from services.adapters.tanium_sq_service import TaniumSqService
from test_credentials.test_crowd_strike_credentials import \
    client_details as crowd_strike_client_details
from test_credentials.test_tanium_asset_credentials import \
    CLIENT_DETAILS as tanium_asset_details
from test_credentials.test_tanium_discover_credentials import \
    CLIENT_DETAILS as tanium_discovery_details
from test_credentials.test_tanium_sq_credentials import \
    CLIENT_DETAILS as tanium_sq_details
from test_helpers.file_mock_credentials import FileForCredentialsMock
from ui_tests.tests.ui_consts import (AD_ADAPTER_NAME,
                                      CROWD_STRIKE_ADAPTER,
                                      CROWD_STRIKE_ADAPTER_NAME,
                                      LINUX_QUERY_NAME,
                                      STRESSTEST_ADAPTER,
                                      STRESSTEST_SCANNER_ADAPTER,
                                      TANIUM_ASSET_ADAPTER,
                                      TANIUM_DISCOVERY_ADAPTER,
                                      TANIUM_SQ_ADAPTER, WINDOWS_QUERY_NAME,
                                      JSON_ADAPTER_NAME, STRESSTEST_ADAPTER_NAME, STRESSTEST_SCANNER_ADAPTER_NAME)
from ui_tests.tests.ui_test_base import TestBase


class TestDevicesQueryAdvancedMoreCases(TestBase):

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
        with CrowdStrikeService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(CROWD_STRIKE_ADAPTER_NAME)
            self.adapters_page.create_new_adapter_connection(CROWD_STRIKE_ADAPTER_NAME, crowd_strike_client_details)
            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.click_query_wizard()
            self.devices_page.select_query_adapter(AD_ADAPTER_NAME)
            self.devices_page.select_query_field(self.devices_page.ID_FIELD)
            self.devices_page.select_query_adapter(CROWD_STRIKE_ADAPTER_NAME)
            assert self.devices_page.get_query_field() == self.users_page.ID_FIELD
            self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES)
            self.devices_page.select_query_adapter(AD_ADAPTER_NAME)
            assert self.devices_page.get_query_field() == self.devices_page.FIELD_NETWORK_INTERFACES
            self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN)
            self.devices_page.select_query_adapter(CROWD_STRIKE_ADAPTER_NAME)
            assert self.devices_page.get_query_field() == self.devices_page.FIELD_LAST_SEEN
            self.devices_page.close_dropdown()
            self.devices_page.wait_for_table_to_load()
            self.adapters_page.clean_adapter_servers(CROWD_STRIKE_ADAPTER_NAME, delete_associated_entities=True)

        self.wait_for_adapter_down(CROWD_STRIKE_ADAPTER)

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
            use case : same label on multiple adapters then remove label from one adapter and compare device count
            is lower on label query.
        """

        def set_tanium_adapter_details(name, details):
            tanium_client_details = details.copy()
            tanium_client_details['connectionLabel'] = tanium_client_details.pop('connection_label')
            self.adapters_page.create_new_adapter_connection(name, tanium_client_details)

        with TaniumAssetService().contextmanager(take_ownership=True), \
                TaniumDiscoverService().contextmanager(take_ownership=True), \
                TaniumSqService().contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(TANIUM_SQ_ADAPTER)
            set_tanium_adapter_details(TANIUM_ASSET_ADAPTER, tanium_asset_details)
            set_tanium_adapter_details(TANIUM_DISCOVERY_ADAPTER, tanium_discovery_details)
            set_tanium_adapter_details(TANIUM_SQ_ADAPTER, tanium_sq_details)
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            all_tanium_count = self.devices_page.query_tanium_connection_label(tanium_asset_details)
            # remove label
            self.adapters_page.edit_server_conn_label(TANIUM_DISCOVERY_ADAPTER, 'UPDATE_LABEL')
            self.adapters_page.wait_for_data_collection_toaster_start()
            self.adapters_page.wait_for_data_collection_toaster_absent()
            tanium_discovery_details['connection_label'] = 'UPDATE_LABEL'
            tanium_discovery_count = self.devices_page.query_tanium_connection_label(tanium_discovery_details)
            # verify we have less devices now
            self.devices_page.click_search()
            updated_tanium_count = self.devices_page.query_tanium_connection_label(tanium_asset_details)
            assert all_tanium_count - tanium_discovery_count == updated_tanium_count
