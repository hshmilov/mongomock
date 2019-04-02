from ui_tests.tests.ui_test_base import TestBase
from axonius.utils.wait import wait_until
from services.plugins.general_info_service import GeneralInfoService
from test_credentials.json_file_credentials import (DEVICE_FIRST_IP,
                                                    DEVICE_THIRD_IP,
                                                    DEVICE_MAC,
                                                    DEVICE_FIRST_VLAN_TAGID,
                                                    DEVICE_SECOND_VLAN_NAME)


class TestDevicesQuery(TestBase):
    SEARCH_TEXT_WINDOWS = 'windows'
    SEARCH_TEXT_TESTDOMAIN = 'testdomain'
    ERROR_TEXT_QUERY_BRACKET = 'Missing {direction} bracket'

    def test_bad_subnet(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_IPS)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_SUBNET)
        self.devices_page.fill_query_value('1.1.1.1')
        self.devices_page.find_element_by_text('Specify <address>/<CIDR> to filter IP by subnet')
        self.devices_page.click_search()

    def test_devices_query_wizard_default_operators(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()
        self.devices_page.select_query_adapter(self.devices_page.VALUE_ADAPTERS_AD)
        assert self.devices_page.get_query_field() == self.devices_page.ID_FIELD
        assert self.devices_page.get_query_comp_op() == self.devices_page.QUERY_COMP_EXISTS

    def test_saved_queries_execute(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_queries_page.switch_to_page()
        self.devices_page.wait_for_spinner_to_end()
        windows_query_row = self.devices_queries_page.find_query_row_by_name('Windows Operating System')
        windows_filter = self.devices_queries_page.find_query_filter_in_row(windows_query_row)
        self.devices_page.wait_for_spinner_to_end()
        windows_query_row.click()
        assert 'devices' in self.driver.current_url and 'query' not in self.driver.current_url
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.find_search_value() == windows_filter
        assert all(x == self.devices_page.VALUE_OS_WINDOWS for x in
                   self.devices_page.get_column_data(self.devices_page.FIELD_OS_TYPE))
        self.devices_page.fill_filter('linux')
        self.devices_page.open_search_list()
        self.devices_page.select_query_by_name('Linux Operating System')
        self.devices_page.wait_for_spinner_to_end()
        assert not len(self.devices_page.get_column_data(self.devices_page.FIELD_OS_TYPE))

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

    def _test_comp_op_change(self):
        """
        Testing that change of the comparison function resets the value, since its type may be different to previous
        """
        self.devices_page.select_query_field(self.devices_page.FIELD_ADAPTERS)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_SIZE)
        self.devices_page.fill_query_value('2')
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS)
        assert not self.devices_page.get_query_value()

    def _test_and_expression(self):
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.select_query_adapter(self.users_page.VALUE_ADAPTERS_JSON, parent=expressions[0])
        self.devices_page.wait_for_spinner_to_end()
        results_count = len(self.devices_page.get_all_data())
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND)
        self.devices_page.select_query_adapter(self.users_page.VALUE_ADAPTERS_AD, parent=expressions[1])
        self.devices_page.wait_for_spinner_to_end()
        assert len(self.devices_page.get_all_data()) <= results_count
        self.devices_page.clear_query_wizard()

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

    def _test_query_brackets(self):
        self.devices_page.add_query_expression()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 3
        self.devices_page.select_query_adapter(self.users_page.VALUE_ADAPTERS_JSON, parent=expressions[0])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_OR)
        self.devices_page.select_query_adapter(self.users_page.VALUE_ADAPTERS_AD, parent=expressions[1])
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
        self.devices_page.toggle_right_bracket(expressions[1])
        assert self.devices_page.is_query_error()
        self.devices_page.clear_query_wizard()

    def _test_remove_query_expressions(self):
        self.devices_page.add_query_expression()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 3
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_IPS, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_SUBNET, parent=expressions[0])
        self.devices_page.fill_query_value('192.168.0.0/16', parent=expressions[0])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND)
        self.devices_page.select_query_adapter(self.users_page.VALUE_ADAPTERS_AD, parent=expressions[1])
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

    def _test_not_expression(self):
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_CONTAINS, parent=expressions[0])
        self.devices_page.fill_query_value('test', parent=expressions[0])
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
        self.devices_page.fill_query_value(DEVICE_FIRST_IP, conditions[1])
        conditions = self.devices_page.find_conditions(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_MAC, conditions[2])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_CONTAINS, conditions[2])
        self.devices_page.fill_query_value(DEVICE_MAC, conditions[2])
        self.devices_page.wait_for_table_to_load()
        assert len(self.devices_page.get_all_data()) == 1

        # DEVICE_MAC and DEVICE_THIRD_IP are not on same Network Interface, so Device will not return
        self.devices_page.fill_query_value(DEVICE_THIRD_IP, conditions[1])
        assert len(self.devices_page.get_all_data()) == 0

        # However, this MAC and IP will return the device, when not using the OBJ feature
        self.devices_page.clear_query_wizard()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_IPS, expressions[0])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EQUALS, expressions[0])
        self.devices_page.fill_query_value(DEVICE_THIRD_IP, expressions[0])
        self.devices_page.select_query_logic_op(self.devices_page.QUERY_LOGIC_AND, expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_MAC, expressions[1])
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_CONTAINS, expressions[1])
        self.devices_page.fill_query_value(DEVICE_MAC, expressions[1])
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
        self.devices_page.fill_query_value(DEVICE_SECOND_VLAN_NAME, conditions[1])
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
        self.devices_page.fill_query_value(DEVICE_SECOND_VLAN_NAME, conditions[1])
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

    def test_query_wizard_combos(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()

        self._test_complex_obj()
        self._test_comp_op_change()
        self._test_and_expression()
        self._test_last_seen_query()
        self._test_query_brackets()
        self._test_remove_query_expressions()
        self._test_not_expression()

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
        for os_type in self.devices_page.get_column_data(self.devices_page.FIELD_OS_TYPE):
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
        self.devices_page.select_query_adapter(self.users_page.VALUE_ADAPTERS_JSON, parent=expressions[0])
        fields = list(self.devices_page.get_all_fields_in_field_selection())
        assert 'Cloud ID' not in fields
        assert 'Last Seen' in fields
        assert 'AD Use DES Key Only' not in fields
        self.devices_page.select_query_adapter(self.users_page.VALUE_ADAPTERS_AD, parent=expressions[0])
        fields = list(self.devices_page.get_all_fields_in_field_selection())
        assert 'AD Use DES Key Only' in fields
