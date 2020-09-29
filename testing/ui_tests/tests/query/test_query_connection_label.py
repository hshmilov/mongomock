import pytest

from axonius.utils.wait import wait_until
from json_file_adapter.service import FILE_NAME
from services.adapters.csv_service import CsvService
from test_credentials.test_aws_credentials_mock import aws_json_file_mock_devices
from test_credentials.test_csv_credentials import CSV_FIELDS
from test_helpers.file_mock_credentials import FileForCredentialsMock
from ui_tests.tests.query.query_test_base import QueryTestBase
from ui_tests.tests.ui_consts import (COMP_EQUALS, COMP_IN, COMP_EXISTS,
                                      LABEL_CLIENT_WITH_SAME_ID,
                                      CSV_PLUGIN_NAME, CSV_NAME)


class TestQueryConnectionLabel(QueryTestBase):
    CONNECTION_LABEL = 'AXON'
    CONNECTION_LABEL_UPDATED = 'AXON2'

    def test_connection_label_query(self):
        """
        USE CASES :  add new AWS mock client with connection label
        test operator equal,exists,in
                      check negative with in
        update client connection label and check with eqal
        delete client connection label and check with in no match

        """
        # JSON FILE - AWS mock
        aws_json_mock_with_label = aws_json_file_mock_devices.copy()
        aws_json_mock_with_label[FILE_NAME] = self.CONNECTION_LABEL
        aws_json_mock_with_label['connectionLabel'] = self.CONNECTION_LABEL

        self.adapters_page.add_json_server(aws_json_mock_with_label)

        # check equal
        wait_until(
            lambda: self.devices_page.get_device_count_by_connection_label(
                operator=COMP_EQUALS,
                value=self.CONNECTION_LABEL) != 0)

        # check exists
        wait_until(
            lambda: self.devices_page.get_device_count_by_connection_label(
                operator=COMP_EXISTS,
                value=self.CONNECTION_LABEL) != 0)

        # check operator in positive value
        wait_until(lambda: self.devices_page.get_device_count_by_connection_label(
            operator=COMP_IN, value=self.CONNECTION_LABEL) != 0)

        # update adapter client connection label
        self.adapters_page.update_json_file_server_connection_label(client_name=self.CONNECTION_LABEL,
                                                                    update_label=self.CONNECTION_LABEL_UPDATED)

        # check operator in negative - previous label
        wait_until(lambda: self.devices_page.get_device_count_by_connection_label(
            operator=COMP_IN, value=self.CONNECTION_LABEL) == 0)

        wait_until(
            lambda: self.devices_page.get_device_count_by_connection_label(
                operator=COMP_EQUALS,
                value=self.CONNECTION_LABEL_UPDATED) != 0)

        # clear adapter client connection label
        self.adapters_page.update_json_file_server_connection_label(client_name=self.CONNECTION_LABEL,
                                                                    update_label='')

        # expect label should be removed from drop down list
        self.devices_page.check_connection_label_removed(self.CONNECTION_LABEL_UPDATED)
        self.adapters_page.remove_json_extra_server(aws_json_mock_with_label)

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
