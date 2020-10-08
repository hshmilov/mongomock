from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytest

from axonius.utils.wait import wait_until
from json_file_adapter.service import FILE_NAME, DEVICES_DATA
from services.adapters.csv_service import CsvService
from test_credentials.test_aws_credentials_mock import aws_json_file_mock_devices
from test_credentials.test_csv_credentials import CSV_FIELDS
from test_credentials.json_file_credentials import DEVICE_FIRST_NAME
from test_helpers.file_mock_credentials import FileForCredentialsMock
from test_helpers.file_mock_helper import FileMockHelper
from ui_tests.tests.query.query_test_base import QueryTestBase
from ui_tests.tests.ui_consts import (COMP_EQUALS, AD_ADAPTER_NAME, JSON_ADAPTER_NAME,
                                      LABEL_CLIENT_WITH_SAME_ID, CSV_PLUGIN_NAME, CSV_NAME,
                                      COMP_EXISTS, COMP_IN, LOGIC_OR)


class TestQueryConnectionLabel(QueryTestBase):
    CONNECTION_LABEL = 'AXON'
    CONNECTION_LABEL_UPDATED = 'AXON2'
    AD_CONNECTION_LABEL = 'AD Label'
    JSON_CONNECTION_LABEL = 'JSON Label'
    JSON_ADDITIONAL_CONNECTION_LABEL = 'JSON Additional Label'

    def test_connection_label_query(self):
        """
        USE CASES :  add new AWS mock client with connection label
        test operator equal,exists,in
                      check negative with in
        update client connection label and check with eqal
        delete client connection label and check with in no match

        """
        self._test_basic_connection_label_functionality()
        self._test_same_connection_label_different_adapters()
        self._test_same_adapter_different_connection_labels()

    def _test_basic_connection_label_functionality(self):
        # JSON FILE - AWS mock
        aws_json_mock_with_label = aws_json_file_mock_devices.copy()
        aws_json_mock_with_label[FILE_NAME] = self.CONNECTION_LABEL
        aws_json_mock_with_label['connectionLabel'] = self.CONNECTION_LABEL

        self.adapters_page.add_json_server(aws_json_mock_with_label, run_discovery_at_last=False)

        devices_count = FileMockHelper.get_mock_devices_count(aws_json_mock_with_label[DEVICES_DATA])

        # check equal
        wait_until(
            lambda: self.devices_page.get_device_count_by_connection_label(
                operator=COMP_EQUALS,
                value=self.CONNECTION_LABEL) == devices_count)

        # check exists
        wait_until(
            lambda: self.devices_page.get_device_count_by_connection_label(
                operator=COMP_EXISTS,
                value=self.CONNECTION_LABEL) == devices_count)

        # check operator in positive value
        wait_until(lambda: self.devices_page.get_device_count_by_connection_label(
            operator=COMP_IN, value=self.CONNECTION_LABEL) == devices_count)

        # update adapter client connection label
        self.adapters_page.update_json_file_server_connection_label(client_name=self.CONNECTION_LABEL,
                                                                    update_label=self.CONNECTION_LABEL_UPDATED)

        # check operator in negative - previous label
        wait_until(lambda: self.devices_page.get_device_count_by_connection_label(
            operator=COMP_IN, value=self.CONNECTION_LABEL) != devices_count)

        wait_until(
            lambda: self.devices_page.get_device_count_by_connection_label(
                operator=COMP_EQUALS,
                value=self.CONNECTION_LABEL_UPDATED) == devices_count)

        # clear adapter client connection label
        self.adapters_page.update_json_file_server_connection_label(client_name=self.CONNECTION_LABEL,
                                                                    update_label='')

        # expect label should be removed from drop down list
        self.devices_page.check_connection_label_removed(self.CONNECTION_LABEL_UPDATED)
        self.adapters_page.remove_json_extra_server(aws_json_mock_with_label)

    def _test_same_connection_label_different_adapters(self):
        # Set connection label 'AD Label' for both json file and active directory adapters
        self.adapters_page.edit_server_conn_label(JSON_ADAPTER_NAME, self.AD_CONNECTION_LABEL, False)
        self.adapters_page.edit_server_conn_label(AD_ADAPTER_NAME, self.AD_CONNECTION_LABEL, False)
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        self.devices_page.select_query_adapter(AD_ADAPTER_NAME)
        self.devices_page.wait_for_table_to_be_responsive()
        total_ad_devices = self.devices_page.count_entities()
        # Check that filtering for AD devices with the connection label returns all the AD devices
        self.devices_page.set_connection_label_query(adapter=AD_ADAPTER_NAME,
                                                     operator=COMP_EQUALS,
                                                     value=self.AD_CONNECTION_LABEL)
        assert self.devices_page.count_entities() == total_ad_devices
        # Check that filtering for JSON file devices with the connection label returns
        # only the single relevant json file record
        self.devices_page.set_connection_label_query(JSON_ADAPTER_NAME,
                                                     COMP_EQUALS,
                                                     self.AD_CONNECTION_LABEL)
        self._assert_single_json_record_result(DEVICE_FIRST_NAME)
        # Same check but this time with the 'EXISTS' operator
        self.devices_page.set_connection_label_query(JSON_ADAPTER_NAME,
                                                     COMP_EXISTS,
                                                     self.AD_CONNECTION_LABEL)
        self._assert_single_json_record_result(DEVICE_FIRST_NAME)
        # Same check but this time with the 'IN' operator
        self.devices_page.set_connection_label_query(JSON_ADAPTER_NAME,
                                                     COMP_IN,
                                                     self.AD_CONNECTION_LABEL)
        self._assert_single_json_record_result(DEVICE_FIRST_NAME)
        # When filtering for any devices (aggregated option) that has the connection label,
        # Check that we get BOTH AD and JSON file devices
        self.devices_page.set_connection_label_query(operator=COMP_EQUALS,
                                                     value=self.AD_CONNECTION_LABEL)
        assert self.devices_page.count_entities() == total_ad_devices + 1
        self.adapters_page.edit_server_conn_label(JSON_ADAPTER_NAME, '', False)
        self.adapters_page.edit_server_conn_label(AD_ADAPTER_NAME, '', False)

    def _assert_single_json_record_result(self, asset_name):
        assert self.devices_page.count_entities() == 1
        assert asset_name in self.devices_page.get_column_data_slicer(self.devices_page.FIELD_ASSET_NAME)

    def _test_same_adapter_different_connection_labels(self):
        # Set connection label 'JSON Label' for the first json file client details
        self.adapters_page.edit_server_conn_label(JSON_ADAPTER_NAME, self.JSON_CONNECTION_LABEL, False)
        # Add an additional json server with 'JSON Additional Label' connection label
        additional_json_client_details = self._get_client_details_for_json(self.JSON_ADDITIONAL_CONNECTION_LABEL)
        self.adapters_page.add_json_server(additional_json_client_details)
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        # Check filtering for 'JSON Label'
        self.devices_page.set_connection_label_query(JSON_ADAPTER_NAME,
                                                     COMP_EQUALS,
                                                     self.JSON_CONNECTION_LABEL)
        self._assert_single_json_record_result(DEVICE_FIRST_NAME)
        # Check filtering for 'JSON Additional Label'
        self.devices_page.set_connection_label_query(JSON_ADAPTER_NAME,
                                                     COMP_EQUALS,
                                                     self.JSON_ADDITIONAL_CONNECTION_LABEL)
        self._assert_single_json_record_result(self.JSON_ADDITIONAL_CONNECTION_LABEL)
        # Same check but this time for asset entity
        self.devices_page.build_connection_label_asset_entity_query(JSON_ADAPTER_NAME,
                                                                    self.JSON_ADDITIONAL_CONNECTION_LABEL,
                                                                    COMP_EQUALS)
        self.devices_page.wait_for_table_to_be_responsive()
        # This time check with 'IN' operator
        self._assert_single_json_record_result(self.JSON_ADDITIONAL_CONNECTION_LABEL)
        self.devices_page.build_connection_label_asset_entity_query(JSON_ADAPTER_NAME,
                                                                    self.JSON_CONNECTION_LABEL,
                                                                    COMP_IN)
        self.devices_page.wait_for_table_to_be_responsive()
        self._assert_single_json_record_result(DEVICE_FIRST_NAME)
        # This time check with 'EXISTS' operator
        # We are supposed to receive both json file records this time.
        self.devices_page.build_connection_label_asset_entity_query(JSON_ADAPTER_NAME,
                                                                    '',
                                                                    COMP_EXISTS)
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.count_entities() == 2
        self.devices_page.clear_query_wizard()
        # Filter devices using a combined query of adapter level and asset entity level.
        # First query chooses all json file adapters with the 'JSON Label'
        self.devices_page.set_connection_label_query(JSON_ADAPTER_NAME,
                                                     COMP_EQUALS,
                                                     self.JSON_CONNECTION_LABEL)
        self.devices_page.add_query_expression()
        self.devices_page.select_query_logic_op(LOGIC_OR)
        # Second query chooses all json file adapters with the 'JSON Additional Label'
        # This query works on the asset entity level
        self.devices_page.build_connection_label_asset_entity_query(JSON_ADAPTER_NAME,
                                                                    self.JSON_ADDITIONAL_CONNECTION_LABEL,
                                                                    COMP_IN,
                                                                    1)
        # We are expected to receive both records
        assert self.devices_page.count_entities() == 2
        self.devices_page.close_dropdown()
        self.adapters_page.remove_json_extra_server(additional_json_client_details)

    @staticmethod
    def _get_client_details_for_json(connection_label):
        future_date = (datetime.utcnow() + relativedelta(years=+10)).strftime('%Y-%m-%d %H:%M:%SZ')
        return {
            FILE_NAME: 'test_last_seen_next_days',
            DEVICES_DATA: FileForCredentialsMock(DEVICES_DATA, '''
               {
                   "devices" : [{
                       "id": "''' + connection_label + '''",
                       "name": "''' + connection_label + '''",
                       "hostname": "''' + connection_label + '''",
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
            'connectionLabel': connection_label
        }

    @pytest.mark.skip('AX-9476')
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
                operator=COMP_EQUALS, value=LABEL_CLIENT_WITH_SAME_ID)

            # update label for csv mock
            self.adapters_page.update_csv_connection_label(file_name=LABEL_CLIENT_WITH_SAME_ID,
                                                           update_label='UPDATE_LABEL')

            update_devices_by_label = self.devices_page.get_device_count_by_connection_label(
                operator=COMP_EQUALS, value=LABEL_CLIENT_WITH_SAME_ID)
            assert update_devices_by_label < devices_by_label

            # update label for aws json file
            self.adapters_page.update_json_file_server_connection_label(client_name=LABEL_CLIENT_WITH_SAME_ID,
                                                                        update_label='UPDATE_LABEL')

            update_devices_by_label = self.devices_page.get_device_count_by_connection_label(
                operator=COMP_EQUALS, value='UPDATE_LABEL')
            assert update_devices_by_label == devices_by_label

            self.adapters_page.clean_adapter_servers(CSV_NAME, True)

        self.wait_for_adapter_down(CSV_PLUGIN_NAME)
        self.adapters_page.remove_json_extra_server(aws_json_mock_with_label)
