import json
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta

from axonius.devices.msft_versions import ENUM_WINDOWS_VERSIONS
from json_file_adapter.service import FILE_NAME, DEVICES_DATA
from test_helpers.file_mock_credentials import FileForCredentialsMock
from ui_tests.tests.query.query_test_base import QueryTestBase
from ui_tests.tests.ui_consts import (COMP_EQUALS, JSON_ADAPTER_NAME, COMP_GREATER_THAN, COMP_LESS_THAN)


class TestQueryOsDistribution(QueryTestBase):
    WINDOWS_VERSION_ASSET_NAME = 'windows_version'
    DUMMY_VALUE = 'dummy'

    def test_windows_os_distribution_lt_gt(self):
        # First, we add a device json adapter connection that returns a mock of all windows versions.
        # Each device in this mock is associated with each of the windows versions.
        json_file_mock_windows_versions_credentials = self._get_windows_versions_details_for_json()
        self.adapters_page.add_json_server(json_file_mock_windows_versions_credentials)
        self.devices_page.switch_to_page()

        # Filter the devices table so that only the devices from the above mock would appear
        self.devices_page.build_query_with_adapter(self.devices_page.FIELD_ASSET_NAME,
                                                   self.WINDOWS_VERSION_ASSET_NAME,
                                                   COMP_EQUALS,
                                                   JSON_ADAPTER_NAME)
        # We sort by the last seen field so that the devices would be displayed in the same order is in the enum
        self.devices_page.click_sort_column(self.devices_page.FIELD_LAST_SEEN)
        self.devices_page.click_query_wizard()
        self.devices_page.add_query_expression()

        # We choose the middle element in the windows versions enum list
        middle_windows_version_index = int(len(ENUM_WINDOWS_VERSIONS) / 2)
        chosen_windows_version = ENUM_WINDOWS_VERSIONS[middle_windows_version_index]

        # Select all devices with windows versions higher than the middle version element
        self.devices_page.build_os_distribution_lt_gt_query(JSON_ADAPTER_NAME,
                                                            chosen_windows_version,
                                                            COMP_GREATER_THAN,
                                                            1)
        self.devices_page.close_dropdown()
        self.devices_page.open_edit_columns()
        self.devices_page.add_columns([self.devices_page.FIELD_OS_DISTRIBUTION])
        self.devices_page.close_edit_columns()

        # Assert that the returned results match all the windows versions above middle element
        assert self.devices_page.get_column_data_slicer(self.devices_page.FIELD_OS_DISTRIBUTION) == \
            ENUM_WINDOWS_VERSIONS[:middle_windows_version_index][::-1]

        # Select all devices with windows versions lower than the middle version element
        self.devices_page.click_query_wizard()
        self.devices_page.build_os_distribution_lt_gt_query(JSON_ADAPTER_NAME,
                                                            chosen_windows_version,
                                                            COMP_LESS_THAN,
                                                            1)
        self.devices_page.close_dropdown()

        # Assert that the returned results match all the windows versions below middle element
        assert self.devices_page.get_column_data_slicer(self.devices_page.FIELD_OS_DISTRIBUTION) == \
            ENUM_WINDOWS_VERSIONS[middle_windows_version_index + 1:][::-1]

        # Choose all windows devices with versions higher than the highest version
        self.devices_page.click_query_wizard()
        self.devices_page.build_os_distribution_lt_gt_query(JSON_ADAPTER_NAME,
                                                            ENUM_WINDOWS_VERSIONS[0],
                                                            COMP_GREATER_THAN,
                                                            1)
        self.devices_page.close_dropdown()

        # Assert that no results are returned for this case
        assert self.devices_page.get_table_count() == 0

        # Choose all windows devices with versions lower than the lowest version
        self.devices_page.click_query_wizard()
        self.devices_page.build_os_distribution_lt_gt_query(JSON_ADAPTER_NAME,
                                                            ENUM_WINDOWS_VERSIONS[-1],
                                                            COMP_LESS_THAN,
                                                            1)
        self.devices_page.close_dropdown()

        # Assert that no results are returned for this case
        assert self.devices_page.get_table_count() == 0

        # Check that switching to the "equals" operator clears the enum value and vice versa
        self.devices_page.click_query_wizard()
        self.devices_page.select_query_field(self.devices_page.FIELD_OS_DISTRIBUTION)
        self.devices_page.select_query_comp_op(COMP_EQUALS)
        self.devices_page.fill_query_string_value(self.DUMMY_VALUE)
        self.devices_page.select_query_comp_op(COMP_LESS_THAN)
        assert self.devices_page.get_query_value(is_enum_value=True) == self.devices_page.QUERY_VALUE_ENUM_INITIAL
        self.devices_page.select_query_value_without_search(chosen_windows_version)
        self.devices_page.select_query_comp_op(COMP_EQUALS)
        assert self.devices_page.get_query_value(input_type_string=True) == ''
        self.devices_page.close_dropdown()

        self.adapters_page.remove_json_extra_server(json_file_mock_windows_versions_credentials)

    def _get_windows_versions_details_for_json(self):
        future_date = (datetime.utcnow() + relativedelta(years=+10))
        device_list = []
        for windows_version in ENUM_WINDOWS_VERSIONS:
            random_mac_address = ':'.join('%02x' % random.randint(0, 255) for x in range(6))
            future_date_str = future_date.strftime('%Y-%m-%d %H:%M:%SZ')
            device_list.append({'id': windows_version,
                                'name': self.WINDOWS_VERSION_ASSET_NAME,  # this name will be used to filter later
                                'hostname': windows_version,
                                'last_seen': future_date_str,
                                'os': {
                                    'distribution': windows_version
                                },
                                'network_interfaces': [{
                                    'mac': random_mac_address,
                                    'ips': ['172.21.12.12']
                                }]})

            # Increasing the date by one minute so we can later sort by the lase seen field in order
            # to maintain the enum order
            future_date = future_date + relativedelta(minutes=+1)

        return {
            FILE_NAME: 'test_query_os_distribution',
            DEVICES_DATA: FileForCredentialsMock(DEVICES_DATA, '''
               {
                   "devices" : ''' + json.dumps(device_list) + ''',
                   "fields" : ["id", "network_interfaces", "name", "hostname", "last_seen"],
                   "additional_schema" : [],
                   "raw_fields" : []
                       }
               '''),
        }
