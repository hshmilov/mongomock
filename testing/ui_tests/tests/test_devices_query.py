from ui_tests.tests.ui_test_base import TestBase


class TestDevicesQuery(TestBase):
    SEARCH_TEXT_WINDOWS = 'windows'
    SEARCH_TEXT_TESTDOMAIN = 'testdomain'
    ERROR_TEXT_QUERY_BRACKET = 'Missing {direction} bracket'

    def test_bad_subnet(self):
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_IPS)
        self.devices_page.select_query_comp_op('subnet')
        self.devices_page.fill_query_value('1.1.1.1')
        self.devices_page.find_element_by_text('Specify <address>/<CIDR> to filter IP by subnet')
        self.devices_page.click_search()

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
        assert all(x == 'Windows' for x in self.devices_page.get_column_data(self.devices_page.FIELD_OS_TYPE))
        self.devices_page.fill_filter('linux')
        self.devices_page.open_search_list()
        self.devices_page.select_query_by_name('Linux Operating System')
        self.devices_page.wait_for_spinner_to_end()
        assert not len(self.devices_page.get_column_data(self.devices_page.FIELD_OS_TYPE))

    def _check_search_text_result(self, text):
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
        self.devices_page.select_query_comp_op('size')
        self.devices_page.fill_query_value('2')
        self.devices_page.select_query_comp_op('equals')
        assert not self.devices_page.get_query_value()

    def _test_and_expression(self):
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.select_query_adapter(self.users_page.VALUE_ADAPTERS_JSON, parent=expressions[0])
        self.devices_page.wait_for_spinner_to_end()
        results_count = len(self.devices_page.get_all_data())
        self.devices_page.select_query_logic_op('and')
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
        self.devices_page.select_query_logic_op('and')
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
        self.devices_page.select_query_logic_op('or')
        self.devices_page.select_query_adapter(self.users_page.VALUE_ADAPTERS_AD, parent=expressions[1])
        self.devices_page.toggle_left_bracket(expressions[0])
        assert self.devices_page.is_text_error(self.ERROR_TEXT_QUERY_BRACKET.format(direction='right'))
        self.devices_page.toggle_right_bracket(expressions[1])
        assert self.devices_page.is_text_error()
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[2])
        self.devices_page.select_query_comp_op('days', parent=expressions[2])
        self.devices_page.fill_query_value(30, parent=expressions[2])
        self.devices_page.select_query_logic_op('and', parent=expressions[2])
        self.devices_page.remove_query_expression(expressions[0])
        assert self.devices_page.is_text_error(self.ERROR_TEXT_QUERY_BRACKET.format(direction='left'))
        self.devices_page.toggle_right_bracket(expressions[1])
        assert self.devices_page.is_text_error()
        self.devices_page.clear_query_wizard()

    def _test_remove_query_expressions(self):
        self.devices_page.add_query_expression()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 3
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES_IPS, parent=expressions[0])
        self.devices_page.select_query_comp_op('subnet', parent=expressions[0])
        self.devices_page.fill_query_value('192.168.0.0', parent=expressions[0])
        self.devices_page.select_query_logic_op('and')
        self.devices_page.select_query_adapter(self.users_page.VALUE_ADAPTERS_AD, parent=expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[2])
        self.devices_page.select_query_comp_op('days', parent=expressions[2])
        self.devices_page.fill_query_value(30, parent=expressions[2])
        self.devices_page.select_query_logic_op('and', parent=expressions[2])
        self.devices_page.wait_for_spinner_to_end()
        assert self.devices_page.is_text_error()
        assert len(self.devices_page.get_all_data())
        self.devices_page.remove_query_expression(expressions[2])
        assert self.devices_page.is_text_error()
        assert len(self.devices_page.get_all_data())
        self.devices_page.remove_query_expression(expressions[0])
        assert self.devices_page.is_text_error()
        assert len(self.devices_page.get_all_data())
        self.devices_page.clear_query_wizard()

    def test_query_wizard_combos(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()

        self._test_comp_op_change()
        self._test_and_expression()
        self._test_last_seen_query()
        self._test_query_brackets()
        self._test_remove_query_expressions()
