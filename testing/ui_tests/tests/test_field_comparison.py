import pytest
from dateutil import parser
from selenium.common.exceptions import NoSuchElementException

from services.adapters.json_file_service import JsonFileService
from ui_tests.tests.test_adapters import JSON_NAME
from ui_tests.tests.ui_consts import AD_ADAPTER_NAME
from ui_tests.tests.ui_test_base import TestBase
from test_credentials.test_esx_credentials import esx_json_file_mock_devices

QUERY_COMP_GREATER_DAYS_THAN = '> Days'
QUERY_COMP_LESS_DAYS_THAN = '< Days'


class TestFieldComparison(TestBase):
    # pylint: disable=too-many-statements
    def test_regular_field_comparison(self):
        with JsonFileService().contextmanager(take_ownership=True):
            self.adapters_page.add_server(esx_json_file_mock_devices, JSON_NAME)
            self.adapters_page.wait_for_server_green(position=2)
            self.adapters_page.wait_for_table_to_load()
            self.adapters_page.wait_for_data_collection_toaster_absent()

            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.click_query_wizard()
            expression = self.devices_page.find_expressions()[0]
            self.devices_page.select_context_cmp(expression)

            with pytest.raises(NoSuchElementException):
                # No Complex fields
                self.devices_page.select_query_field(self.devices_page.FIELD_ADAPTER_PROPERTIES, parent=expression)
            self.devices_page.safe_refresh()

            self.devices_page.click_query_wizard()
            expression = self.devices_page.find_expressions()[0]
            self.devices_page.select_context_cmp(expression)
            with pytest.raises(NoSuchElementException):
                # Aggregated adapter (specific_data) should be sliced
                self.devices_page.select_query_adapter(self.devices_page.GENERAL_DATA_TAB_TITLE, select_num=0)
            self.devices_page.safe_refresh()

            self.devices_page.click_query_wizard()
            expression = self.devices_page.find_expressions()[0]
            self.devices_page.select_context_cmp(expression)
            self.devices_page.select_query_adapter(AD_ADAPTER_NAME, select_num=0)
            self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expression)
            with pytest.raises(NoSuchElementException):
                # Not a date-time format field
                self.devices_page.select_query_field(
                    self.devices_page.FIELD_HOSTNAME_TITLE, parent=expression, select_num=1)
            self.devices_page.safe_refresh()

            # Field is not date-time type
            self.devices_page.click_query_wizard()
            expression = self.devices_page.find_expressions()[0]
            self.devices_page.select_context_cmp(expression)
            self.devices_page.select_query_adapter(AD_ADAPTER_NAME, select_num=0)
            self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=expression)
            self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_GREATER_THAN)
            # Make sure the options menu opened, which means the options we wanted to choose is not available
            assert len(self.devices_page.find_elements_by_css(self.devices_page.QUERY_CONDITIONS_OPTIONS_CSS)) == 1
            self.devices_page.safe_refresh()

            self.devices_page.click_query_wizard()
            expression = self.devices_page.find_expressions()[0]
            self.devices_page.select_context_cmp(expression)
            self.devices_page.select_query_adapter(AD_ADAPTER_NAME, select_num=0)
            self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expression)
            self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_GREATER_THAN)
            self.devices_page.select_query_adapter(JSON_NAME, select_num=1)
            self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expression, select_num=1)
            self.devices_page.click_search()
            self.devices_page.wait_for_table_to_load()
            grater_count = self.devices_page.get_table_count()
            self.devices_page.reset_query()
            self.devices_page.click_query_wizard()
            expression = self.devices_page.find_expressions()[0]
            self.devices_page.select_context_cmp(expression)
            self.devices_page.select_query_adapter(AD_ADAPTER_NAME, select_num=0)
            self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expression)
            self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_LESS_THAN)
            self.devices_page.select_query_adapter(JSON_NAME, select_num=1)
            self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expression, select_num=1)
            self.devices_page.click_search()
            self.devices_page.wait_for_table_to_load()
            less_count = self.devices_page.get_table_count()
            assert grater_count or less_count

            self.devices_page.reset_query()
            self.devices_page.click_query_wizard()
            expression = self.devices_page.find_expressions()[0]
            self.devices_page.select_context_cmp(expression)
            self.devices_page.select_query_adapter(AD_ADAPTER_NAME, select_num=0)
            self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=expression)
            self.devices_page.select_query_adapter(JSON_NAME, select_num=1)
            self.devices_page.select_query_field(
                self.devices_page.FIELD_HOSTNAME_TITLE, parent=expression, select_num=1)
            self.devices_page.click_search()
            self.devices_page.wait_for_table_to_load()
            assert self.devices_page.get_table_count() > 0
            self.adapters_page.remove_server(ad_client=esx_json_file_mock_devices, adapter_name=JSON_NAME,
                                             expected_left=1, delete_associated_entities=True,
                                             adapter_search_field=self.adapters_page.JSON_FILE_SERVER_SEARCH_FIELD)

    def test_complex_field_comparison(self):
        with JsonFileService().contextmanager(take_ownership=True):
            self.adapters_page.add_server(esx_json_file_mock_devices, JSON_NAME)
            self.adapters_page.wait_for_server_green(position=2)
            self.adapters_page.wait_for_table_to_load()
            self.adapters_page.wait_for_data_collection_toaster_absent()

            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            grater = True
            self.devices_page.click_query_wizard()
            expression = self.devices_page.find_expressions()[0]
            self.devices_page.select_context_cmp(expression)
            self.devices_page.select_query_adapter(AD_ADAPTER_NAME, select_num=0)
            self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expression)
            self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_GREATER_THAN)
            self.devices_page.select_query_adapter(JSON_NAME, select_num=1)
            self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expression, select_num=1)
            self.devices_page.click_search()
            self.devices_page.wait_for_table_to_load()
            # adapters_data.active_directory_adapter.last_seen > adapters_data.json_file_adapter.last_seen
            if self.devices_page.get_table_count() == 0:
                # adapters_data.active_directory_adapter.last_seen < adapters_data.json_file_adapter.last_seen
                self.devices_page.click_query_wizard()
                self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_LESS_THAN)
                self.devices_page.click_search()
                grater = False
            self.devices_page.wait_for_table_to_load()
            assert self.devices_page.get_table_count() > 0
            self.devices_page.click_expand_row()
            last_seens = self.devices_page.get_column_data_expand_row(self.devices_page.FIELD_LAST_SEEN)
            assert last_seens and len(last_seens[0].split('\n')) == 2
            hostname = self.devices_page.get_column_data_expand_row(self.devices_page.FIELD_HOSTNAME_TITLE)[0]
            last_seens = last_seens[0].split('\n')
            ad_last_seen = parser.parse(last_seens[0])
            esx_last_seen = parser.parse(last_seens[1])
            self.devices_page.click_query_wizard()
            self.devices_page.select_query_comp_op(
                QUERY_COMP_GREATER_DAYS_THAN if grater else QUERY_COMP_LESS_DAYS_THAN)
            self.devices_page.fill_field_comparison_query_value('0')
            self.devices_page.click_search()
            # adapters_data.active_directory_adapter.last_seen </> adapters_data.json_file_adapter.last_seen + 0
            self.devices_page.wait_for_table_to_load()
            # Make sure nothing in the table has changed
            assert [x for x in self.devices_page.get_all_data_cells() if hostname in x[2]]
            self.devices_page.click_query_wizard()
            days_diff = (esx_last_seen - ad_last_seen).days
            days_diff += 1 if not grater else -1
            self.devices_page.fill_field_comparison_query_value(str(days_diff))
            # adapters_data.active_directory_adapter.last_seen </> adapters_data.json_file_adapter.last_seen + days_diff
            self.devices_page.click_search()
            self.devices_page.wait_for_table_to_load()
            # Now it should now be in the table anymore
            assert not [x for x in self.devices_page.get_all_data_cells() if hostname in x[2]]
            self.adapters_page.remove_server(ad_client=esx_json_file_mock_devices, adapter_name=JSON_NAME,
                                             expected_left=1, delete_associated_entities=True,
                                             adapter_search_field=self.adapters_page.JSON_FILE_SERVER_SEARCH_FIELD)
