import random
import math
from datetime import datetime
from uuid import uuid4

from selenium.common.exceptions import NoSuchElementException
from axonius.utils.hash import get_preferred_quick_adapter_id
from axonius.utils.wait import wait_until
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import (AD_ADAPTER_NAME,
                                      JSON_ADAPTER_NAME,
                                      WINDOWS_QUERY_NAME,
                                      STRESSTEST_SCANNER_ADAPTER,
                                      STRESSTEST_ADAPTER, LINUX_QUERY_NAME)
from services.plugins.general_info_service import GeneralInfoService
from services.adapters.cisco_service import CiscoService
from services.adapters.esx_service import EsxService
from services.adapters.cylance_service import CylanceService
from services.adapters import stresstest_scanner_service, stresstest_service
from test_credentials.json_file_credentials import (DEVICE_FIRST_IP,
                                                    DEVICE_THIRD_IP,
                                                    DEVICE_MAC,
                                                    DEVICE_SUBNET,
                                                    DEVICE_FIRST_VLAN_TAGID,
                                                    DEVICE_SECOND_VLAN_NAME)
from devops.scripts.automate_dev import credentials_inputer


class TestDevicesQuery(TestBase):
    SEARCH_TEXT_WINDOWS = 'windows'
    SEARCH_TEXT_TESTDOMAIN = 'testdomain'
    ERROR_TEXT_QUERY_BRACKET = 'Missing {direction} bracket'
    CUSTOM_QUERY = 'Clear_query_test'
    CISCO_PLUGIN_NAME = 'cisco_adapter'
    CISCO_PRETTY_NAME = 'Cisco'
    ESX_PLUGIN_NAME = 'esx_adapter'
    ESX_PRETTY_NAME = 'VMware ESXi'
    CYCLANCE_PLUGIN_NAME = 'cylance_adapter'
    CYCLANCE_PRETTY_NAME = 'CylancePROTECT'

    def test_bad_subnet(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_IPS)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_SUBNET)
        self.devices_page.fill_query_string_value('1.1.1.1')
        self.devices_page.find_element_by_text('Specify <address>/<CIDR> to filter IP by subnet')
        self.devices_page.click_search()

    def test_in_query(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()

        ips = self.devices_page.get_column_data_inline_with_remainder(self.devices_page.FIELD_NETWORK_INTERFACES_IPS)

        self.devices_page.click_query_wizard()
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_IPS)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_IN)
        self.devices_page.fill_query_string_value(','.join(ips))
        self.devices_page.wait_for_table_to_load()
        self.devices_page.wait_for_spinner_to_end()

        self.devices_page.click_search()

        self.devices_page.select_page_size(50)

        new_ips = self.devices_page.get_column_data_inline_with_remainder(
            self.devices_page.FIELD_NETWORK_INTERFACES_IPS)

        assert len([ip for ip in new_ips if ip.strip() == '']) == 0

        ips_set = set(ips)
        new_ips_set = set(new_ips)

        assert ips_set.issubset(new_ips_set)

        for ips in self.devices_page.get_column_cells_data_inline_with_remainder(
                self.devices_page.FIELD_NETWORK_INTERFACES_IPS):
            if isinstance(ips, list):
                assert len(ips_set.intersection(set(ips))) > 0
            else:
                assert ips in ips_set

    def test_in_adapters_query(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()

        self.devices_page.select_page_size(50)

        all_adapters = set(self.devices_page.get_column_data_inline_with_remainder(self.devices_page.FIELD_ADAPTERS))
        adapters = random.sample(all_adapters, math.ceil(len(all_adapters) / 2))

        self.devices_page.click_query_wizard()
        self.devices_page.select_query_field(self.devices_page.FIELD_ADAPTERS)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_IN)
        self.devices_page.fill_query_string_value(','.join(adapters))
        self.devices_page.wait_for_table_to_load()
        self.devices_page.wait_for_spinner_to_end()

        self.devices_page.click_search()

        self.devices_page.select_page_size(50)

        new_adapters = set(self.devices_page.get_column_data_inline_with_remainder(
            self.devices_page.FIELD_ADAPTERS))

        assert len([adapter for adapter in new_adapters if adapter.strip() == '']) == 0

        assert set(adapters).issubset(new_adapters)

        for adapters_values in self.devices_page.get_column_cells_data_inline_with_remainder(
                self.devices_page.FIELD_ADAPTERS):
            if isinstance(adapters_values, list):
                assert len(set(adapters_values).intersection(set(adapters))) > 0
            else:
                assert adapters_values in adapters

    def test_in_with_delimiter_query(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()

        self.devices_page.click_row_checkbox()

        special_tag = 'a\\,b'

        self.devices_page.add_new_tags(['a\\,b'])

        self.devices_page.click_query_wizard()
        self.devices_page.select_query_field(self.devices_page.FIELD_TAGS)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_IN)
        self.devices_page.fill_query_string_value(special_tag)
        self.devices_page.wait_for_table_to_load()
        self.devices_page.wait_for_spinner_to_end()

        self.devices_page.click_search()

        assert self.devices_page.count_entities() == 1

    def test_devices_query_wizard_default_operators(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()
        self.devices_page.select_query_adapter(AD_ADAPTER_NAME)
        assert self.devices_page.get_query_field() == self.devices_page.ID_FIELD
        assert self.devices_page.get_query_comp_op() == self.devices_page.QUERY_COMP_EXISTS

    def test_devices_query_wizard_list_field(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_USED_USERS)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_STARTS)
        self.devices_page.fill_query_string_value('test')
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == 1
        self.devices_page.fill_query_string_value('test 3')
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == 0

    def _check_search_text_result(self, text):
        self.devices_page.wait_for_table_to_load()
        all_data = self.devices_page.get_all_data()
        assert len(all_data)
        assert any(text in x.lower() for x in all_data)

    def test_search_everywhere(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.fill_filter(self.SEARCH_TEXT_WINDOWS)
        self.devices_page.enter_search()
        self._check_search_text_result(self.SEARCH_TEXT_WINDOWS)
        self.devices_page.fill_filter(self.SEARCH_TEXT_TESTDOMAIN)
        self.devices_page.open_search_list()
        self.devices_page.select_search_everywhere()
        self._check_search_text_result(self.SEARCH_TEXT_TESTDOMAIN)
        self.devices_page.click_query_wizard()
        self._check_search_text_result(self.SEARCH_TEXT_TESTDOMAIN)

    def _test_comp_op_change(self):
        """
        Testing that change of the comparison function resets the value, since its type may be different to previous
        """
        self.devices_page.select_query_field(self.devices_page.FIELD_ADAPTERS)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_SIZE)
        self.devices_page.fill_query_value('2')
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS)
        assert not self.devices_page.get_query_value()

    def _test_adapters_filter_change_icon(self):
        """
        Testing the change in the field type icon - when using the adapters filter the icon changes to a special icon
        """
        assert not self.devices_page.is_filtered_adapter_icon_exists()
        self.devices_page.click_on_filter_adapter(JSON_ADAPTER_NAME)
        assert self.devices_page.is_filtered_adapter_icon_exists()
        self.devices_page.clear_query_wizard()
        expressions = self.devices_page.find_expressions()
        self.devices_page.toggle_obj(expressions[0])
        assert not self.devices_page.is_filtered_adapter_icon_exists()
        self.devices_page.click_on_filter_adapter(JSON_ADAPTER_NAME)
        assert self.devices_page.is_filtered_adapter_icon_exists()
        self.devices_page.toggle_obj(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, parent=expressions[0])
        assert self.devices_page.is_filtered_adapter_icon_exists()
        self.devices_page.clear_query_wizard()

    def _test_and_expression(self):
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.select_query_adapter(JSON_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.wait_for_spinner_to_end()
        results_count = len(self.devices_page.get_all_data())
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND)
        self.devices_page.select_query_adapter(AD_ADAPTER_NAME, parent=expressions[1])
        self.devices_page.wait_for_spinner_to_end()
        assert len(self.devices_page.get_all_data()) <= results_count
        self.devices_page.clear_query_wizard()

    def check_all_columns_exist(self, columns_list):
        assert all(column in self.devices_page.get_columns_header_text() for column in columns_list)

    def check_no_columns_exist(self, columns_list):
        assert not any(column in self.devices_page.get_columns_header_text() for column in columns_list)

    def edit_columns(self, column_list):
        self.devices_page.edit_columns(add_col_names=column_list,
                                       adapter_title=self.devices_page.VALUE_ADAPTERS_GENERAL)

    def _create_query(self):
        self.devices_page.click_query_wizard()
        self.users_page.add_query_expression()
        self.users_page.add_query_expression()

        expressions = self.devices_page.find_expressions()
        self.devices_page.toggle_not(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_OS_MAJOR, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS)

        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_OS_BUILD, parent=expressions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, parent=expressions[1])

        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, expressions[2])
        self.devices_page.select_query_field(self.devices_page.FIELD_PART_OF_DOMAIN, parent=expressions[2])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_TRUE, parent=expressions[2])
        self.devices_page.click_search()

    def test_clear_query_wizard(self):
        columns_list = [self.devices_page.FIELD_OS_MAJOR, self.devices_page.FIELD_OS_BUILD,
                        self.devices_page.FIELD_PART_OF_DOMAIN]
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.check_no_columns_exist(columns_list)
        self.edit_columns(columns_list)
        self.check_all_columns_exist(columns_list)
        self._create_query()
        self.devices_page.wait_for_table_to_load()
        self.check_all_columns_exist(columns_list)
        self.devices_page.save_query_as(self.CUSTOM_QUERY)
        assert self.devices_page.find_query_title_text() == self.CUSTOM_QUERY
        self.devices_page.click_query_wizard()
        self.devices_page.clear_query_wizard()
        select = self.driver.find_element_by_css_selector(self.devices_page.QUERY_FIELD_VALUE)
        assert select.text == self.devices_page.CHART_QUERY_FIELD_DEFAULT
        self.devices_page.click_search()
        self.devices_page.wait_for_table_to_load()
        self.check_all_columns_exist(columns_list)
        assert self.devices_page.find_query_title_text() == 'New Query'

    def test_host_name_and_adapter_filters_query(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, parent=expressions[0])
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.wait_for_table_to_load()
        results_count = self.devices_page.count_entities()
        self.devices_page.click_on_clear_all_filter_adapters(parent=expressions[0])
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.wait_for_table_to_load()
        assert results_count == self.devices_page.count_entities()
        self.devices_page.click_on_select_all_filter_adapters(parent=expressions[0])
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.wait_for_table_to_load()
        assert results_count == self.devices_page.count_entities()

        self.devices_page.click_on_filter_adapter(AD_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.wait_for_table_to_load()

        non_ad_count = self.devices_page.count_entities()
        assert results_count > non_ad_count
        self.devices_page.click_on_filter_adapter(AD_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.click_on_filter_adapter(JSON_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.wait_for_table_to_load()
        non_json_count = self.devices_page.count_entities()
        assert results_count > non_json_count
        assert non_json_count > non_ad_count

        self.devices_page.click_search()

        host_name_query = 'test host name'
        self.devices_page.click_save_query()
        self.devices_page.fill_query_name(host_name_query)
        self.devices_page.click_save_query_save_button()

        self.devices_page.click_query_wizard()
        self.devices_page.clear_query_wizard()
        self.devices_page.click_search()

        self.devices_page.execute_saved_query(host_name_query)

        self.devices_page.click_query_wizard()
        assert self.devices_page.is_filtered_adapter_icon_exists()

    def test_obj_network_and_adapter_filters_query(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.toggle_obj(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES, parent=expressions[0])
        conditions = self.devices_page.find_conditions(expressions[0])
        assert len(conditions) == 2
        self.devices_page.select_query_field(self.devices_page.FIELD_IPS, conditions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, conditions[1])
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.wait_for_table_to_load()
        results_count = self.devices_page.count_entities()
        self.devices_page.click_on_filter_adapter(AD_ADAPTER_NAME, parent=expressions[0])
        assert results_count > self.devices_page.count_entities()

    def _test_last_seen_query(self):
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[0])
        self.devices_page.select_query_comp_op('days', parent=expressions[0])
        self.devices_page.fill_query_value(365, parent=expressions[0])
        self.devices_page.wait_for_spinner_to_end()
        results_count = len(self.devices_page.get_all_data())
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND)
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[1])
        self.devices_page.select_query_comp_op('days', parent=expressions[1])
        self.devices_page.fill_query_value(1, parent=expressions[1])
        self.devices_page.wait_for_spinner_to_end()
        assert len(self.devices_page.get_all_data()) < results_count
        self.devices_page.clear_query_wizard()

    def _test_last_seen_query_with_filter_adapters(self):
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[0])
        self.devices_page.select_query_comp_op('days', parent=expressions[0])
        self.devices_page.fill_query_value(365, parent=expressions[0])
        self.devices_page.wait_for_table_to_load()
        results_count = len(self.devices_page.get_all_data())
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND)
        self.devices_page.click_on_select_all_filter_adapters(parent=expressions[1])
        self.devices_page.click_on_filter_adapter(AD_ADAPTER_NAME, parent=expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[1])
        self.devices_page.select_query_comp_op('days', parent=expressions[1])
        self.devices_page.fill_query_value(1, parent=expressions[1])
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_search_value().count(self.devices_page.NAME_ADAPTERS_AD) == 1
        assert len(self.devices_page.get_all_data()) < results_count

        self.devices_page.click_on_select_all_filter_adapters(parent=expressions[0])
        self.devices_page.click_on_filter_adapter(JSON_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.wait_for_spinner_to_end()
        assert len(self.devices_page.get_all_data()) == 0
        assert self.devices_page.find_search_value().count(self.devices_page.NAME_ADAPTERS_AD) == 1
        assert self.devices_page.find_search_value().count(self.devices_page.NAME_ADAPTERS_JSON) == 1

        self.devices_page.clear_query_wizard()

    def _test_asset_name_query_with_filter_adapters(self):
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.toggle_not(expressions[0])
        self.devices_page.click_on_select_all_filter_adapters(parent=expressions[0])
        self.devices_page.click_on_filter_adapter(AD_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_ASSET_NAME, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, parent=expressions[0])
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.wait_for_table_to_load()
        assert len(self.devices_page.get_all_data()) > 1
        assert self.devices_page.find_search_value().count(self.devices_page.NAME_ADAPTERS_AD) == 1

        self.devices_page.clear_query_wizard()

    def _test_query_brackets(self):
        self.devices_page.add_query_expression()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 3
        self.devices_page.select_query_adapter(JSON_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_OR)
        self.devices_page.select_query_adapter(AD_ADAPTER_NAME, parent=expressions[1])
        self.devices_page.toggle_left_bracket(expressions[0])
        assert self.devices_page.is_query_error(self.ERROR_TEXT_QUERY_BRACKET.format(direction='right'))
        self.devices_page.toggle_right_bracket(expressions[1])
        assert self.devices_page.is_query_error()
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[2])
        self.devices_page.select_query_comp_op('days', parent=expressions[2])
        self.devices_page.fill_query_value(30, parent=expressions[2])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, parent=expressions[2])
        self.devices_page.remove_query_expression(expressions[0])
        assert self.devices_page.is_query_error(self.ERROR_TEXT_QUERY_BRACKET.format(direction='left'))
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.toggle_right_bracket(expressions[0])
        assert self.devices_page.is_query_error()
        self.devices_page.clear_query_wizard()

    def _test_remove_query_expressions(self):
        self.devices_page.add_query_expression()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 3
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_IPS, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_SUBNET, parent=expressions[0])
        self.devices_page.fill_query_string_value('192.168.0.0/16', parent=expressions[0])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND)
        self.devices_page.select_query_adapter(AD_ADAPTER_NAME, parent=expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[2])
        self.devices_page.select_query_comp_op('exists', parent=expressions[2])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, parent=expressions[2])
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data())
        current_filter = self.devices_page.find_search_value()
        self.devices_page.remove_query_expression(expressions[2])
        assert current_filter != self.devices_page.find_search_value()
        current_filter = self.devices_page.find_search_value()
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data())
        self.devices_page.remove_query_expression(expressions[0])
        assert current_filter != self.devices_page.find_search_value()
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data())
        self.devices_page.clear_query_wizard()

    def _test_remove_query_expression_does_not_reset_values(self):
        self.devices_page.add_query_expression()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 3
        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_CONTAINS, parent=expressions[0])
        self.devices_page.fill_query_string_value('test', parent=expressions[0])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_OR, parent=expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[1])
        self.devices_page.select_query_comp_op(self.users_page.QUERY_COMP_DAYS, parent=expressions[1])
        self.devices_page.fill_query_value('1', parent=expressions[1])
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_OR, parent=expressions[2])
        self.devices_page.select_query_field(self.devices_page.FIELD_ASSET_NAME, parent=expressions[2])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, parent=expressions[2])
        self.devices_page.fill_query_string_value('test_device', parent=expressions[2])
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.remove_query_expression(expressions[0])
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.is_query_error()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        assert self.devices_page.get_query_value(parent=expressions[0]) == '1'
        assert self.devices_page.get_query_value(parent=expressions[1], input_type_string=True) == 'test_device'
        self.devices_page.clear_query_wizard()

    def _test_not_expression(self):
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_CONTAINS, parent=expressions[0])
        self.devices_page.fill_query_string_value('test', parent=expressions[0])
        self.devices_page.toggle_not(expressions[0])
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 1
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND)
        self.devices_page.select_query_field(self.devices_page.FIELD_SAVED_QUERY, parent=expressions[1])
        self.devices_page.select_query_value(WINDOWS_QUERY_NAME, parent=expressions[1])
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.is_query_error()
        assert not len(self.devices_page.get_all_data())
        self.devices_page.toggle_not(expressions[1])
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 1
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 3
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, parent=expressions[2])
        self.devices_page.select_query_field(self.devices_page.FIELD_ASSET_NAME, parent=expressions[2])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, parent=expressions[2])
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 1
        self.devices_page.toggle_not(expressions[2])
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.is_query_error()
        assert not len(self.devices_page.get_all_data())
        self.devices_page.clear_query_wizard()

    def _test_complex_obj(self):
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1

        # Prepare OBJ query with 2 nested conditions
        self.devices_page.toggle_obj(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES, expressions[0])
        self.devices_page.add_query_obj_condition(expressions[0])
        conditions = self.devices_page.find_conditions(expressions[0])
        assert len(conditions) == 3

        # DEVICE_MAC and DEVICE_FIRST_IP are on same Network Interface, so Device will return
        self.devices_page.select_query_field(self.devices_page.FIELD_IPS, conditions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, conditions[1])
        self.devices_page.fill_query_string_value(DEVICE_FIRST_IP, conditions[1])
        conditions = self.devices_page.find_conditions(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_MAC, conditions[2])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_CONTAINS, conditions[2])
        self.devices_page.fill_query_string_value(DEVICE_MAC, conditions[2])
        self.devices_page.wait_for_table_to_load()
        assert len(self.devices_page.get_all_data()) == 1

        # DEVICE_THIRD_IP and SUBNETS are not on same Network Interface, so Device will not return
        self.devices_page.fill_query_string_value(DEVICE_THIRD_IP, conditions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_SUBNETS, conditions[2])
        self.devices_page.fill_query_string_value(DEVICE_SUBNET, conditions[2])
        self.devices_page.wait_for_table_to_load()
        assert len(self.devices_page.get_all_data()) == 0

        # However, this IP and VLAN will return the device, when not using the OBJ feature
        self.devices_page.clear_query_wizard()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_IPS, expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, expressions[0])
        self.devices_page.fill_query_string_value(DEVICE_THIRD_IP, expressions[0])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_SUBNETS, expressions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_CONTAINS, expressions[1])
        self.devices_page.fill_query_string_value(DEVICE_SUBNET, expressions[1])
        self.devices_page.wait_for_table_to_load()
        assert len(self.devices_page.get_all_data()) == 1
        self.devices_page.clear_query_wizard()

        self._test_complex_obj_subnets()
        self._test_complex_obj_vlans()
        self._test_complex_obj_dates()

    def _test_complex_obj_subnets(self):
        # Network Interfaces -> Subnets exists should return results
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.toggle_obj(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES, expressions[0])
        conditions = self.devices_page.find_conditions(expressions[0])
        assert len(conditions) == 2
        self.devices_page.select_query_field(self.devices_page.FIELD_SUBNETS, conditions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, conditions[1])
        self.devices_page.wait_for_table_to_load()
        assert len(self.devices_page.get_all_data())
        self.devices_page.clear_query_wizard()

    def _test_complex_obj_vlans(self):
        # DEVICE_FIRST_TAGID and DEVICE_SECOND_VLAN_NAME are on same Network Interface and different Vlan, so:
        # Network Interfaces -> Vlans: Vlan Name and Vlans: Tag ID - returns result, however:
        # Network Interfaces: Vlans -> Vlan Name and Tag ID - does not
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.toggle_obj(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES, expressions[0])
        self.devices_page.add_query_obj_condition()
        conditions = self.devices_page.find_conditions(expressions[0])
        assert len(conditions) == 3
        self.devices_page.select_query_field(self.devices_page.FIELD_VLANS_VLAN_NAME, conditions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, conditions[1])
        self.devices_page.fill_query_string_value(DEVICE_SECOND_VLAN_NAME, conditions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_VLANS_TAG_ID, conditions[2])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, conditions[2])
        self.devices_page.fill_query_value(DEVICE_FIRST_VLAN_TAGID, conditions[2])
        self.devices_page.wait_for_table_to_load()
        assert len(self.devices_page.get_all_data())
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_VLANS, expressions[0])
        self.devices_page.add_query_obj_condition()
        conditions = self.devices_page.find_conditions(expressions[0])
        assert len(conditions) == 3
        self.devices_page.select_query_field(self.devices_page.FIELD_VLAN_NAME, conditions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, conditions[1])
        self.devices_page.fill_query_string_value(DEVICE_SECOND_VLAN_NAME, conditions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_TAG_ID, conditions[2])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, conditions[2])
        self.devices_page.fill_query_value(DEVICE_FIRST_VLAN_TAGID, conditions[2])
        self.devices_page.wait_for_table_to_load()
        assert not len(self.devices_page.get_all_data())
        self.devices_page.clear_query_wizard()

    def _test_complex_obj_dates(self):
        self.devices_page.close_dropdown()
        with GeneralInfoService().contextmanager(take_ownership=True):
            self.enforcements_page.create_run_wmi_scan_on_each_cycle_enforcement()
            self.base_page.run_discovery()

            # Wait for WMI info
            self.devices_page.switch_to_page()
            self.devices_page.fill_filter(self.devices_page.AD_WMI_ADAPTER_FILTER)
            self.devices_page.enter_search()
            self.devices_page.wait_for_table_to_load()
            wait_until(self.devices_page.get_all_data, total_timeout=60 * 25)
            # Refresh to have the Users field available (not automatically fetched)
            self.devices_page.refresh()
            self.devices_page.wait_for_table_to_load()

            # Start building complex query
            self.devices_page.click_query_wizard()
            self.devices_page.add_query_expression()
            expressions = self.devices_page.find_expressions()
            assert len(expressions) == 2

            self.devices_page.toggle_obj(expressions[0])
            self.devices_page.select_query_field(self.devices_page.FIELD_USERS, expressions[0])
            conditions = self.devices_page.find_conditions(expressions[0])
            assert len(conditions) == 2
            self.devices_page.select_query_field(self.devices_page.FIELD_USERS_LAST_USE, conditions[1])
            self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_DAYS, conditions[1])
            self.devices_page.fill_query_value(2, conditions[1])
            self.devices_page.wait_for_table_to_load()
            assert len(self.devices_page.get_all_data())

            self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_OR)
            self.devices_page.toggle_obj(expressions[1])
            self.devices_page.select_query_field(self.devices_page.FIELD_USERS, expressions[1])
            conditions = self.devices_page.find_conditions(expressions[1])
            assert len(conditions) == 2
            self.devices_page.select_query_field(self.devices_page.FIELD_USERS_LAST_USE, conditions[1])
            self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_DAYS, conditions[1])
            self.devices_page.fill_query_value(5, conditions[1])
            self.devices_page.wait_for_table_to_load()
            assert len(self.devices_page.get_all_data())
            self.devices_page.clear_query_wizard()

    def _test_adapters_size(self):
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_query_field(self.devices_page.FIELD_ADAPTERS)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_SIZE)
        self.devices_page.fill_query_value('1')
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.is_query_error()

        assert len(self.devices_page.get_all_data()) == 20
        self.devices_page.fill_query_value('2')
        self.devices_page.wait_for_table_to_load()
        assert len(self.devices_page.get_all_data()) == 0
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_SIZE_BELOW)
        self.devices_page.wait_for_table_to_load()
        assert len(self.devices_page.get_all_data()) == 20
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_SIZE_ABOVE)
        self.devices_page.wait_for_table_to_load()
        assert len(self.devices_page.get_all_data()) == 0
        self.devices_page.fill_query_value('1')
        self.devices_page.wait_for_table_to_load()
        assert len(self.devices_page.get_all_data()) == 0
        self.devices_page.fill_query_value('0')
        self.devices_page.wait_for_table_to_load()
        assert len(self.devices_page.get_all_data()) == 20
        self.devices_page.clear_query_wizard()

    def test_query_wizard_combos(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, WINDOWS_QUERY_NAME)
        self.devices_page.reset_query()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()
        self._test_adapters_filter_change_icon()
        self._test_complex_obj()
        self._test_comp_op_change()
        self._test_and_expression()
        self._test_last_seen_query()
        self._test_last_seen_query_with_filter_adapters()
        self._test_asset_name_query_with_filter_adapters()
        self._test_query_brackets()
        self._test_remove_query_expressions()
        self._test_remove_query_expression_does_not_reset_values()
        self._test_not_expression()
        self._test_adapters_size()
        self._test_enum_expressions()

    def _assert_query(self, expected_query):
        current_query = self.devices_page.find_query_search_input().get_attribute('value')
        assert current_query == expected_query

    def _perform_query_scenario(self, field, value, comp_op, field_type, expected_query, subfield=None, obj=False):
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        if obj:
            self.devices_page.toggle_obj(expressions[0])
        self.devices_page.select_query_field(field, expressions[0])
        conditions = self.devices_page.find_conditions()
        if len(conditions) == 2 and subfield:
            self.devices_page.select_query_field(subfield, conditions[1])
        self.devices_page.select_query_comp_op(comp_op, expressions[0])
        if field_type == 'string':
            self.devices_page.select_query_value(value, expressions[0])
        elif field_type == 'integer':
            self.devices_page.select_query_value_without_search(value, expressions[0])
        assert self.devices_page.is_query_error()
        self.devices_page.wait_for_table_to_load()
        self._assert_query(expected_query)

    def _test_enum_expressions(self):
        combo_configs = [
            # enum of type string
            {'field': self.devices_page.FIELD_ADAPTERS,
             'comp_op': self.devices_page.QUERY_COMP_EQUALS,
             'value': 'Cisco',
             'field_type': 'string',
             'expected_query': '(adapters == "cisco_adapter")'},
            # enum of type string
            {'field': 'Port Access: Port Mode',
             'comp_op': self.devices_page.QUERY_COMP_EQUALS,
             'value': 'singleHost',
             'field_type': 'string',
             'expected_query': '(specific_data.data.port_access.port_mode == "singleHost")'},
            # enum of type string - displayed as Object (field and subfield)
            {'field': 'Port Access',
             'subfield': 'Port Mode',
             'comp_op': self.devices_page.QUERY_COMP_EQUALS,
             'value': 'singleHost',
             'field_type': 'string',
             'obj': True,
             'expected_query': '(specific_data.data.port_access == match([(port_mode == "singleHost")]))'},
            # enum of type string - displayed flat
            {'field': 'Agent Versions: Name',
             'comp_op': self.devices_page.QUERY_COMP_EQUALS,
             'value': 'Cylance Agent',
             'field_type': 'string',
             'expected_query': '(specific_data.data.agent_versions.adapter_name == "Cylance Agent")'},
            # enum of type string - displayed as Object (field and subfield)
            {'field': 'Agent Versions',
             'subfield': 'Name',
             'comp_op': self.devices_page.QUERY_COMP_EQUALS,
             'value': 'Cylance Agent',
             'field_type': 'string',
             'obj': True,
             'expected_query':
                 '(specific_data.data.agent_versions == match([(adapter_name == "Cylance Agent")]))'},
            # enum of type integer
            {'field': self.devices_page.FIELD_OS_BITNESS,
             'comp_op': self.devices_page.QUERY_COMP_EQUALS,
             'value': '64',
             'field_type': 'integer',
             'expected_query': '(specific_data.data.os.bitness == 64)'}
        ]
        try:
            with CiscoService().contextmanager(take_ownership=True), \
                    EsxService().contextmanager(take_ownership=True),\
                    CylanceService().contextmanager(take_ownership=True):
                credentials_inputer.main()
                self.settings_page.switch_to_page()
                self.base_page.run_discovery()
                self.devices_page.switch_to_page()
                for conf in combo_configs:
                    self.devices_page.click_query_wizard()
                    self.devices_page.clear_query_wizard()
                    self._perform_query_scenario(**conf)
                    self.devices_page.click_search()
                self.devices_page.click_query_wizard()
                self.devices_page.clear_query_wizard()
                for conf in combo_configs:
                    try:
                        self.driver.find_element_by_css_selector('.expression-obj.light.active')
                        self.devices_page.toggle_obj(self.devices_page.find_expressions()[0])
                    except NoSuchElementException:
                        # Nothing to do
                        pass
                    self._perform_query_scenario(**conf)
                self.devices_page.click_search()
        finally:
            self.adapters_page.clean_adapter_servers(self.CISCO_PRETTY_NAME)
            self.wait_for_adapter_down(self.CISCO_PLUGIN_NAME)
            self.adapters_page.clean_adapter_servers(self.ESX_PRETTY_NAME)
            self.wait_for_adapter_down(self.ESX_PLUGIN_NAME)
            self.adapters_page.clean_adapter_servers(self.CYCLANCE_PRETTY_NAME)
            self.wait_for_adapter_down(self.CYCLANCE_PLUGIN_NAME)

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
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.is_query_error()
        for os_type in self.devices_page.get_column_data_slicer(self.devices_page.FIELD_OS_TYPE):
            assert os_type == self.devices_page.VALUE_OS_WINDOWS

        self.devices_page.select_query_value(LINUX_QUERY_NAME, parent=expressions[0])
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.is_query_error()
        assert not len(self.devices_page.get_all_data())

    def test_empty_fields_arent_there(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()

        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1

        self.devices_page.select_query_adapter(self.devices_page.VALUE_ADAPTERS_GENERAL, parent=expressions[0])
        fields = list(self.devices_page.get_all_fields_in_field_selection())
        # swap_cached is only returned by chef, not by AD or JSON
        assert 'Total Swap GB' not in fields
        assert 'Host Name' in fields

        self.devices_page.select_query_adapter(JSON_ADAPTER_NAME, parent=expressions[0])
        fields = list(self.devices_page.get_all_fields_in_field_selection())
        assert 'Last Contact' in fields
        assert 'Cloud ID' not in fields
        assert 'Last Seen' not in fields
        assert 'AD Use DES Key Only' not in fields

        self.devices_page.select_query_adapter(AD_ADAPTER_NAME, parent=expressions[0])
        fields = list(self.devices_page.get_all_fields_in_field_selection())
        assert 'AD Use DES Key Only' in fields

    def test_save_query(self):
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.toggle_left_bracket(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_IPS, expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, expressions[0])
        self.devices_page.fill_query_string_value(DEVICE_THIRD_IP, expressions[0])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_MAC, expressions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_CONTAINS, expressions[1])
        self.devices_page.fill_query_string_value(DEVICE_MAC, expressions[1])
        self.devices_page.toggle_right_bracket(expressions[1])
        assert not self.devices_page.is_query_save_as_disabled()

        self.devices_page.toggle_right_bracket(expressions[1])
        assert self.devices_page.is_query_save_as_disabled()
        self.devices_page.toggle_right_bracket(expressions[1])
        assert not self.devices_page.is_query_save_as_disabled()

    def test_quick_count(self):
        """
        Tests that before calculating the whole count of the query, a quick >1000 is shown
        """
        devices_count = 100 * 1000  # 100k
        db = self.axonius_system.get_devices_db()

        def generate_fake_device(id_):
            data_id_ = f'yay-{id_}'
            return {
                'internal_axon_id': uuid4().hex,
                'accurate_for_datetime': datetime.now(),
                'adapters': [
                    {
                        'client_used': 'yes',
                        'plugin_type': 'Adapter',
                        'plugin_name': 'stresstest_adapter',
                        'plugin_unique_name': 'stresstest_adapter_0',
                        'type': 'entitydata',
                        'accurate_for_datetime': datetime.now(),
                        'quick_id': get_preferred_quick_adapter_id(data_id_, 'stresstest_adapter_0'),
                        'data': {
                            'random_text_for_love_and_prosperity': '19',
                            'id': data_id_,
                            'pretty_id': f'AX-{id_}'
                        }
                    }
                ],
                'tags': [],
                'adapter_list_length': 1
            }

        # inserting a lot of devices
        db.insert_many(generate_fake_device(x)
                       for x
                       in range(devices_count))

        # carefully chosen to be damn slow
        slow_query = ' and '.join(f'adapters_data.stresstest_adapter.random_text_for_love_and_prosperity != "{x}"'
                                  for x
                                  in range(10))

        self.devices_page.switch_to_page()
        self.devices_page.fill_filter(slow_query)
        self.devices_page.enter_search()
        wait_until(lambda: '> 1000' in self.devices_page.get_raw_count_entities())
        assert self.devices_page.count_entities() == devices_count

    def test_adapters_filter_all_vs_clear_selection(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, parent=expressions[0])
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.wait_for_table_to_load()
        results_count = self.devices_page.count_entities()
        self.devices_page.click_on_clear_all_filter_adapters(parent=expressions[0])
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.wait_for_table_to_load()
        query = self.devices_page.find_query_search_input()
        assert results_count == self.devices_page.count_entities()
        self.devices_page.click_on_select_all_filter_adapters(parent=expressions[0])
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.wait_for_table_to_load()
        assert results_count == self.devices_page.count_entities()
        assert query == self.devices_page.find_query_search_input()

    def test_exclude_entities_with_no_query(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()

        self._text_exclude_entities_on_current_data()

    def test_exclude_with_or_query(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()

        self.devices_page.click_query_wizard()

        self.devices_page.add_query_expression()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 3
        self.devices_page.select_query_adapter(JSON_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_OR)
        self.devices_page.select_query_adapter(AD_ADAPTER_NAME, parent=expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[2])
        self.devices_page.select_query_comp_op('exists', parent=expressions[2])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, parent=expressions[2])
        self.devices_page.click_search()
        self.devices_page.wait_for_table_to_load()
        self._text_exclude_entities_on_current_data()

    def test_exclude_clear_query(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()

        self.devices_page.click_query_wizard()

        self.devices_page.add_query_expression()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 3
        self.devices_page.select_query_adapter(JSON_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_OR)
        self.devices_page.select_query_adapter(AD_ADAPTER_NAME, parent=expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[2])
        self.devices_page.select_query_comp_op('exists', parent=expressions[2])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, parent=expressions[2])
        self.devices_page.click_search()
        self.devices_page.wait_for_table_to_load()
        filtered_out_indices = self._text_exclude_entities_on_current_data()
        self.devices_page.click_query_wizard()
        self.devices_page.click_filter_out_clear()
        self.devices_page.wait_for_table_to_load()

        self.devices_page.count_selected_entities()
        for index in filtered_out_indices:
            assert self.devices_page.is_toggle_selected(self.devices_page.get_row_checkbox(index))

    def _text_exclude_entities_on_current_data(self):
        real_devices_count = self.devices_page.count_entities()
        devices_count = real_devices_count
        # limit the number of devices to sample to the first page
        devices_count = devices_count if devices_count <= 20 else 20
        indices = random.sample(range(1, devices_count), math.ceil(devices_count / 3))
        for index in indices:
            self.devices_page.click_row_checkbox(index)
        self.devices_page.open_filter_out_dialog()
        self.devices_page.confirm_filter_out()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == (real_devices_count - len(indices))
        return indices

    def test_in_enum_query(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        try:
            with stress.contextmanager(take_ownership=True), \
                    stress_scanner.contextmanager(take_ownership=True):
                device_dict = {'device_count': 10, 'name': 'blah'}
                stress.add_client(device_dict)
                stress_scanner.add_client(device_dict)

                self.base_page.run_discovery()
                self.base_page.run_discovery()
                self.devices_page.switch_to_page()
                self.devices_page.wait_for_table_to_load()

                self.devices_page.select_page_size(50)

                all_os_types = set(self.devices_page.
                                   get_column_data_inline_with_remainder(self.devices_page.FIELD_OS_TYPE))

                os_types = random.sample(all_os_types, math.ceil(len(all_os_types) / 2))

                self.devices_page.click_query_wizard()
                self.devices_page.select_query_field(self.devices_page.FIELD_OS_TYPE)
                self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_IN)
                self.devices_page.fill_query_string_value(','.join(set(os_types)))
                self.devices_page.wait_for_table_to_load()
                self.devices_page.wait_for_spinner_to_end()

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

        finally:
            self.wait_for_adapter_down(STRESSTEST_ADAPTER)
            self.wait_for_adapter_down(STRESSTEST_SCANNER_ADAPTER)
