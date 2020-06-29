from selenium.common.exceptions import NoSuchElementException

from axonius.consts.gui_consts import ADAPTER_CONNECTIONS_FIELD
from axonius.utils.wait import wait_until
from json_file_adapter.service import FILE_NAME
from ui_tests.pages.entities_page import EntitiesPage
from ui_tests.tests.test_enforcement_config import JSON_NAME
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import (AD_ADAPTER_NAME,
                                      JSON_ADAPTER_NAME,
                                      WINDOWS_QUERY_NAME, JSON_ADAPTER_PLUGIN_NAME)
from services.plugins.general_info_service import GeneralInfoService
from services.adapters.cylance_service import CylanceService
from test_credentials.json_file_credentials import (DEVICE_FIRST_IP,
                                                    DEVICE_THIRD_IP,
                                                    DEVICE_MAC,
                                                    DEVICE_SUBNET,
                                                    DEVICE_FIRST_VLAN_TAGID,
                                                    DEVICE_SECOND_VLAN_NAME,
                                                    DEVICE_FIRST_HOSTNAME,
                                                    DEVICE_FIRST_NAME,
                                                    DEVICE_SECOND_NAME)
from test_credentials.test_esx_credentials import esx_json_file_mock_devices
from test_credentials.test_cisco_credentials import cisco_json_file_mock_credentials
from test_credentials.test_aws_credentials_mock import aws_json_file_mock_devices
from devops.scripts.automate_dev import credentials_inputer


# pylint: disable=C0302
class TestDevicesQueryAdvancedCases(TestBase):
    ERROR_TEXT_QUERY_BRACKET = 'Missing {direction} bracket'
    CISCO_PRETTY_NAME = 'Cisco'
    CISCO_PLUGIN_NAME = 'cisco_adapter'
    ESX_PRETTY_NAME = 'VMware ESXi'
    ESX_PLUGIN_NAME = 'esx_adapter'
    CYCLANCE_PLUGIN_NAME = 'cylance_adapter'
    CYCLANCE_PRETTY_NAME = 'CylancePROTECT'
    CONNECTION_LABEL = 'AXON'
    CONNECTION_LABEL_UPDATED = 'AXON2'

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
        self.devices_page.wait_for_table_to_be_responsive()

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

    def _test_comp_op_change(self):
        """
        Testing that change of the comparison function resets the value, since its type may be different to previous
        """
        self.devices_page.select_query_field(ADAPTER_CONNECTIONS_FIELD)
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
        self.devices_page.select_context_obj(expressions[0])
        assert not self.devices_page.is_filtered_adapter_icon_exists()
        self.devices_page.click_on_filter_adapter(JSON_ADAPTER_NAME)
        assert self.devices_page.is_filtered_adapter_icon_exists()
        self.devices_page.select_context_all(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, parent=expressions[0])
        assert self.devices_page.is_filtered_adapter_icon_exists()
        self.devices_page.clear_query_wizard()

    def _test_and_expression(self):
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.select_query_adapter(JSON_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        results_count = len(self.devices_page.get_all_data())
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND)
        self.devices_page.select_query_adapter(AD_ADAPTER_NAME, parent=expressions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) <= results_count
        self.devices_page.clear_query_wizard()

    def test_host_name_and_adapter_filters_query(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        results_count = self.devices_page.count_entities()
        self.devices_page.click_on_clear_all_filter_adapters(parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert results_count == self.devices_page.count_entities()
        self.devices_page.click_on_select_all_filter_adapters(parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert results_count == self.devices_page.count_entities()

        self.devices_page.click_on_filter_adapter(AD_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()

        non_ad_count = self.devices_page.count_entities()
        assert results_count > non_ad_count
        self.devices_page.click_on_filter_adapter(AD_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.click_on_filter_adapter(JSON_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
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

    def _test_last_seen_query(self, query_comp=EntitiesPage.QUERY_COMP_DAYS, query_value=365):
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[0])
        self.devices_page.select_query_comp_op(query_comp, parent=expressions[0])
        self.devices_page.fill_query_value(query_value, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        results_count = len(self.devices_page.get_all_data())
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND)
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[1])
        self.devices_page.select_query_comp_op(query_comp, parent=expressions[1])
        self.devices_page.fill_query_value(1, parent=expressions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        if query_comp in (EntitiesPage.QUERY_COMP_DAYS, EntitiesPage.QUERY_COMP_HOURS):
            assert len(self.devices_page.get_all_data()) < results_count
        else:
            assert len(self.devices_page.get_all_data()) == results_count
        self.devices_page.clear_query_wizard()

    def _test_last_seen_query_last_days(self):
        self._test_last_seen_query(EntitiesPage.QUERY_COMP_DAYS)

    def _test_last_seen_query_with_next_days(self):
        self._test_last_seen_query(EntitiesPage.QUERY_COMP_NEXT_DAYS)

    def _test_last_seen_query_last_hours(self):
        self._test_last_seen_query(EntitiesPage.QUERY_COMP_HOURS, 365 * 24)

    def _test_last_seen_query_with_next_hours(self):
        self._test_last_seen_query(EntitiesPage.QUERY_COMP_NEXT_HOURS, 365 * 24)

    def _test_last_seen_query_with_filter_adapters(self):
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_DAYS, parent=expressions[0])
        self.devices_page.fill_query_value(365, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        results_count = len(self.devices_page.get_all_data())
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND)
        self.devices_page.click_on_select_all_filter_adapters(parent=expressions[1])
        self.devices_page.click_on_filter_adapter(AD_ADAPTER_NAME, parent=expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_DAYS, parent=expressions[1])
        self.devices_page.fill_query_value(1, parent=expressions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.find_search_value().count(self.devices_page.NAME_ADAPTERS_AD) == 1
        assert len(self.devices_page.get_all_data()) < results_count

        self.devices_page.click_on_select_all_filter_adapters(parent=expressions[0])
        self.devices_page.click_on_filter_adapter(JSON_ADAPTER_NAME, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
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
        self.devices_page.wait_for_table_to_be_responsive()
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
        self.devices_page.select_query_comp_op(EntitiesPage.QUERY_COMP_DAYS, parent=expressions[2])
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
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data())
        current_filter = self.devices_page.find_search_value()
        self.devices_page.remove_query_expression(expressions[2])
        assert current_filter != self.devices_page.find_search_value()
        current_filter = self.devices_page.find_search_value()
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data())
        self.devices_page.remove_query_expression(expressions[0])
        assert current_filter != self.devices_page.find_search_value()
        self.devices_page.wait_for_table_to_be_responsive()
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
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_OR, parent=expressions[2])
        self.devices_page.select_query_field(self.devices_page.FIELD_ASSET_NAME, parent=expressions[2])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, parent=expressions[2])
        self.devices_page.fill_query_string_value('test_device', parent=expressions[2])
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.remove_query_expression(expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
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
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 1
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND)
        self.devices_page.select_query_field(self.devices_page.FIELD_SAVED_QUERY, parent=expressions[1])
        self.devices_page.select_query_value(WINDOWS_QUERY_NAME, parent=expressions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert not len(self.devices_page.get_all_data())
        self.devices_page.toggle_not(expressions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 1
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 3
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, parent=expressions[2])
        self.devices_page.select_query_field(self.devices_page.FIELD_ASSET_NAME, parent=expressions[2])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, parent=expressions[2])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 1
        self.devices_page.toggle_not(expressions[2])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert not len(self.devices_page.get_all_data())
        self.devices_page.clear_query_wizard()

    def _test_complex_obj(self):
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1

        # Prepare OBJ query with 2 nested conditions
        self.devices_page.select_context_obj(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES, expressions[0])
        self.devices_page.add_query_child_condition(expressions[0])
        conditions = self.devices_page.find_conditions(expressions[0])
        assert len(conditions) == 2

        # DEVICE_MAC and DEVICE_FIRST_IP are on same Network Interface, so Device will return
        self.devices_page.select_query_field(self.devices_page.FIELD_IPS, conditions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, conditions[0])
        self.devices_page.fill_query_string_value(DEVICE_FIRST_IP, conditions[0])
        conditions = self.devices_page.find_conditions(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_MAC, conditions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_CONTAINS, conditions[1])
        self.devices_page.fill_query_string_value(DEVICE_MAC, conditions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 1

        # DEVICE_THIRD_IP and SUBNETS are not on same Network Interface, so Device will not return
        self.devices_page.fill_query_string_value(DEVICE_THIRD_IP, conditions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_SUBNETS, conditions[1])
        self.devices_page.fill_query_string_value(DEVICE_SUBNET, conditions[1])
        self.devices_page.wait_for_table_to_be_responsive()
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
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 1
        self.devices_page.clear_query_wizard()

        self._test_complex_obj_subnets()
        self._test_complex_obj_vlans()
        self._test_complex_obj_dates()

    def _test_complex_obj_subnets(self):
        # Network Interfaces -> Subnets exists should return results
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_context_obj(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES, expressions[0])
        conditions = self.devices_page.find_conditions(expressions[0])
        assert len(conditions) == 1
        self.devices_page.select_query_field(self.devices_page.FIELD_SUBNETS, conditions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS, conditions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data())
        self.devices_page.clear_query_wizard()

    def _test_complex_obj_vlans(self):
        # DEVICE_FIRST_TAGID and DEVICE_SECOND_VLAN_NAME are on same Network Interface and different Vlan, so:
        # Network Interfaces -> Vlans: Vlan Name and Vlans: Tag ID - returns result, however:
        # Network Interfaces: Vlans -> Vlan Name and Tag ID - does not
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_context_obj(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES, expressions[0])
        self.devices_page.add_query_child_condition()
        conditions = self.devices_page.find_conditions(expressions[0])
        assert len(conditions) == 2
        self.devices_page.select_query_field(self.devices_page.FIELD_VLANS_VLAN_NAME, conditions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, conditions[0])
        self.devices_page.fill_query_string_value(DEVICE_SECOND_VLAN_NAME, conditions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_VLANS_TAG_ID, conditions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, conditions[1])
        self.devices_page.fill_query_value(DEVICE_FIRST_VLAN_TAGID, conditions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data())
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_VLANS, expressions[0])
        self.devices_page.add_query_child_condition()
        conditions = self.devices_page.find_conditions(expressions[0])
        assert len(conditions) == 2
        self.devices_page.select_query_field(self.devices_page.FIELD_VLAN_NAME, conditions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, conditions[0])
        self.devices_page.fill_query_string_value(DEVICE_SECOND_VLAN_NAME, conditions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_TAG_ID, conditions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, conditions[1])
        self.devices_page.fill_query_value(DEVICE_FIRST_VLAN_TAGID, conditions[1])
        self.devices_page.wait_for_table_to_be_responsive()
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
            self.devices_page.wait_for_table_to_be_responsive()

            wait_until(self.devices_page.get_all_data, total_timeout=60 * 25)
            # Refresh to have the Users field available (not automatically fetched)
            self.devices_page.refresh()
            self.devices_page.wait_for_table_to_be_responsive()

            # Start building complex query
            self.devices_page.click_query_wizard()
            self.devices_page.add_query_expression()
            expressions = self.devices_page.find_expressions()
            assert len(expressions) == 2
            self.devices_page.select_context_obj(expressions[0])
            self.devices_page.select_query_field(self.devices_page.FIELD_USERS, expressions[0])
            conditions = self.devices_page.find_conditions(expressions[0])
            assert len(conditions) == 1
            self.devices_page.select_query_field(self.devices_page.FIELD_USERS_LAST_USE, conditions[0])
            self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_DAYS, conditions[0])
            self.devices_page.fill_query_value(2, conditions[0])
            self.devices_page.wait_for_table_to_be_responsive()

            assert len(self.devices_page.get_all_data())
            self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_OR)
            self.devices_page.select_context_obj(expressions[1])
            self.devices_page.select_query_field(self.devices_page.FIELD_USERS, expressions[1])
            conditions = self.devices_page.find_conditions(expressions[1])
            assert len(conditions) == 1
            self.devices_page.select_query_field(self.devices_page.FIELD_USERS_LAST_USE, conditions[0])
            self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_DAYS, conditions[0])
            self.devices_page.fill_query_value(5, conditions[0])
            self.devices_page.wait_for_table_to_be_responsive()

            assert len(self.devices_page.get_all_data())
            self.devices_page.clear_query_wizard()

    def _test_adapters_size(self):
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_query_field(ADAPTER_CONNECTIONS_FIELD)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_SIZE)
        self.devices_page.fill_query_value('1')
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 20
        self.devices_page.fill_query_value('2')
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 0
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_SIZE_BELOW)
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 20
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_SIZE_ABOVE)
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 0
        self.devices_page.fill_query_value('1')
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 0
        self.devices_page.fill_query_value('0')
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 20
        self.devices_page.clear_query_wizard()
        self.devices_page.safe_refresh()

    def _assert_query(self, expected_query):
        current_query = self.devices_page.find_query_search_input().get_attribute('value')
        assert current_query == expected_query

    def _perform_query_scenario(self, field, value, comp_op, field_type, expected_query, subfield=None, obj=False):
        self.devices_page.change_query_params(field, value, comp_op, field_type, subfield, obj)
        assert self.devices_page.is_query_error()
        self.devices_page.wait_for_table_to_be_responsive()
        self._assert_query(expected_query)

    def _test_enum_expressions(self):
        combo_configs = [
            # enum of type string
            {'field': ADAPTER_CONNECTIONS_FIELD,
             'comp_op': self.devices_page.QUERY_COMP_EQUALS,
             'value': JSON_NAME,
             'field_type': 'string',
             'expected_query': f'(adapters == "{JSON_ADAPTER_PLUGIN_NAME}")'},
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
        with CylanceService().contextmanager(take_ownership=True):
            credentials_inputer.main()
            self.adapters_page.add_server(esx_json_file_mock_devices, JSON_NAME)
            self.adapters_page.wait_for_server_green()
            self.adapters_page.wait_for_table_to_load()
            self.adapters_page.wait_for_data_collection_toaster_absent()
            self.adapters_page.add_server(cisco_json_file_mock_credentials, JSON_NAME)
            self.adapters_page.wait_for_server_green()
            self.adapters_page.wait_for_table_to_load()
            self.adapters_page.wait_for_data_collection_toaster_absent()
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
                    self.driver.find_element_by_css_selector('.expression-context.selected')
                    self.devices_page.select_context_all(self.devices_page.find_expressions()[0])
                except NoSuchElementException:
                    # Nothing to do
                    pass
                self._perform_query_scenario(**conf)
            self.devices_page.click_search()

            self.adapters_page.restore_json_client()
            self.adapters_page.clean_adapter_servers(self.CYCLANCE_PRETTY_NAME)

        self.wait_for_adapter_down(self.CYCLANCE_PLUGIN_NAME)

        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        self.devices_page.clear_query_wizard()

    def _test_asset_entity_expressions(self):
        self.devices_page.click_search()
        self.adapters_page.add_json_extra_client()
        self.base_page.run_discovery()

        # DEVICE_FIRST_HOSTNAME and DEVICE_SECOND_NAME on single Adapter Device - expected to find one
        self.devices_page.build_asset_entity_query(JSON_ADAPTER_NAME,
                                                   self.devices_page.FIELD_HOSTNAME_TITLE,
                                                   DEVICE_FIRST_HOSTNAME,
                                                   self.devices_page.FIELD_ASSET_NAME,
                                                   DEVICE_SECOND_NAME)
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 1
        children = self.devices_page.get_asset_entity_children_first()
        # DEVICE_THIRD_IP and DEVICE_SECOND_NAME on single Adapter Device - expected to find none
        self.devices_page.change_asset_entity_query(children[0],
                                                    self.devices_page.FIELD_NETWORK_INTERFACES_IPS,
                                                    DEVICE_THIRD_IP)
        self.devices_page.wait_for_table_to_be_responsive()
        assert not self.devices_page.get_all_data()
        # DEVICE_THIRD_IP and DEVICE_FIRST_NAME on single Adapter Device - expected to find none
        self.devices_page.change_asset_entity_query(children[1],
                                                    value_string=DEVICE_FIRST_NAME)
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == 1

        self.devices_page.click_search()
        self.adapters_page.restore_json_client()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        self.devices_page.clear_query_wizard()

    def test_adapters_name_sort(self):
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        self.devices_page.open_query_adapters_list_and_open_adapter_filter()
        adapters_list = self.devices_page.get_adapters_secondary_list()

        previous_value = adapters_list[0]
        for value in adapters_list[1:]:
            assert value >= previous_value
            previous_value = value

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
        self._test_last_seen_query_last_days()
        self._test_last_seen_query_with_next_days()
        self._test_last_seen_query_last_hours()
        self._test_last_seen_query_with_next_hours()
        self._test_last_seen_query_with_filter_adapters()
        self._test_asset_name_query_with_filter_adapters()
        self._test_query_brackets()
        self._test_remove_query_expressions()
        self._test_remove_query_expression_does_not_reset_values()
        self._test_not_expression()
        self._test_adapters_size()
        self._test_enum_expressions()
        self._test_asset_entity_expressions()

    def test_change_field_with_different_value_schema(self):
        self.adapters_page.add_server(aws_json_file_mock_devices, JSON_NAME)
        self.adapters_page.wait_for_server_green(position=2)
        self.adapters_page.wait_for_table_to_load()
        self.adapters_page.wait_for_data_collection_toaster_absent()

        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()
        expressions = self.devices_page.find_expressions()
        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=expressions[0])
        self.devices_page.select_query_comp_op('equals', parent=expressions[0])
        self.devices_page.fill_query_string_value('w', parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        query_filter = self.devices_page.find_search_value()
        results_count = len(self.devices_page.get_all_data())
        self.devices_page.select_query_field(self.devices_page.FIELD_FIREWALL_RULES_FROM_PORT,
                                             parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert len(self.devices_page.get_all_data()) == results_count
        assert self.devices_page.find_search_value() == query_filter
        assert self.devices_page.is_query_error(self.devices_page.MSG_ERROR_QUERY_WIZARD)
        self.devices_page.click_search()

        self.adapters_page.remove_server(ad_client=aws_json_file_mock_devices, adapter_name=JSON_NAME,
                                         expected_left=1, delete_associated_entities=True,
                                         adapter_search_field=self.adapters_page.JSON_FILE_SERVER_SEARCH_FIELD)

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

        self.adapters_page.add_json_server(aws_json_mock_with_label, run_discovery_at_last=True, position=2)

        # check equal
        wait_until(
            lambda: self.devices_page.get_device_count_by_connection_label(
                operator=self.devices_page.QUERY_COMP_EQUALS,
                value=self.CONNECTION_LABEL) != 0, total_timeout=200, interval=20
        )

        # check exists
        wait_until(
            lambda: self.devices_page.get_device_count_by_connection_label(
                operator=self.devices_page.QUERY_COMP_EXISTS,
                value=self.CONNECTION_LABEL) != 0, total_timeout=200, interval=20)

        # check operator in positive value
        wait_until(lambda: self.devices_page.get_device_count_by_connection_label(
            operator=self.devices_page.QUERY_COMP_IN, value=self.CONNECTION_LABEL) != 0, total_timeout=200, interval=20)

        # update adapter client connection label
        self.adapters_page.update_json_file_server_connection_label(client_name=self.CONNECTION_LABEL,
                                                                    update_label=self.CONNECTION_LABEL_UPDATED)

        # check operator in negative - previous label
        wait_until(lambda: self.devices_page.get_device_count_by_connection_label(
            operator=self.devices_page.QUERY_COMP_IN, value=self.CONNECTION_LABEL) == 0, total_timeout=200, interval=20)

        wait_until(
            lambda: self.devices_page.get_device_count_by_connection_label(
                operator=self.devices_page.QUERY_COMP_EQUALS,
                value=self.CONNECTION_LABEL_UPDATED) != 0, total_timeout=200, interval=20)

        # clear adapter client connection label
        self.adapters_page.update_json_file_server_connection_label(client_name=self.CONNECTION_LABEL,
                                                                    update_label='')

        # expect label should be removed from drop down list
        wait_until(lambda: self.devices_page.verify_label_does_not_exist(self.CONNECTION_LABEL_UPDATED),
                   check_return_value=True, total_timeout=200, interval=20)

        self.adapters_page.remove_server(ad_client=aws_json_mock_with_label,
                                         adapter_name=JSON_NAME,
                                         delete_associated_entities=True,
                                         expected_left=1,
                                         adapter_search_field=self.adapters_page.JSON_FILE_SERVER_SEARCH_FIELD)
