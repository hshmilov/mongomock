from datetime import datetime
from uuid import uuid4

from axonius.utils.hash import get_preferred_quick_adapter_id
from axonius.utils.wait import wait_until
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import AD_ADAPTER_NAME, JSON_ADAPTER_NAME
from services.plugins.general_info_service import GeneralInfoService
from test_credentials.json_file_credentials import (DEVICE_FIRST_IP,
                                                    DEVICE_THIRD_IP,
                                                    DEVICE_MAC,
                                                    DEVICE_SUBNET,
                                                    DEVICE_FIRST_VLAN_TAGID,
                                                    DEVICE_SECOND_VLAN_NAME)


class TestDevicesQuery(TestBase):
    SEARCH_TEXT_WINDOWS = 'windows'
    SEARCH_TEXT_TESTDOMAIN = 'testdomain'
    ERROR_TEXT_QUERY_BRACKET = 'Missing {direction} bracket'
    CUSTOM_QUERY = 'Clear_query_test'

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
                                       adapter_title='General')

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
        self.devices_page.click_on_select_all_filter_adapters(parent=expressions[0])
        self.devices_page.click_on_filter_adapter(AD_ADAPTER_NAME, parent=expressions[0])
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
        assert self.devices_page.find_search_value().count(self.devices_page.NAME_ADAPTERS_AD) == 2
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
        self.devices_page.select_query_comp_op('days', parent=expressions[2])
        self.devices_page.fill_query_value(30, parent=expressions[2])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, parent=expressions[2])
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data())
        self.devices_page.remove_query_expression(expressions[2])
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data())
        self.devices_page.remove_query_expression(expressions[0])
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
        self.devices_page.select_query_value(self.devices_page.VALUE_SAVED_QUERY_WINDOWS, parent=expressions[1])
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
        self.devices_page.switch_to_page()
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

    def test_saved_query_field(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()

        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_query_field(self.devices_page.FIELD_SAVED_QUERY, parent=expressions[0])
        self.devices_page.select_query_value(self.devices_page.VALUE_SAVED_QUERY_WINDOWS, parent=expressions[0])
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.is_query_error()
        for os_type in self.devices_page.get_column_data_slicer(self.devices_page.FIELD_OS_TYPE):
            assert os_type == self.devices_page.VALUE_OS_WINDOWS

        self.devices_page.select_query_value(self.devices_page.VALUE_SAVED_QUERY_LINUX, parent=expressions[0])
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

        self.devices_page.select_query_adapter('General', parent=expressions[0])
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
