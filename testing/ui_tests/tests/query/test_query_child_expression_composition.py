import time

from test_credentials.json_file_credentials import DEVICE_MAC
from ui_tests.tests.query.query_test_base import QueryTestBase
from ui_tests.tests.ui_consts import (COMP_CONTAINS, COMP_EXISTS, LOGIC_OR)


class TestQueryChildExpressionComposition(QueryTestBase):
    DEVICE_IP_PREFIX = '192'
    IP_FRACTION = '2.1'

    def _prepare_child_expression(self):
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1

        self.devices_page.select_context_obj(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES, expressions[0])
        conditions = self.devices_page.find_conditions(expressions[0])
        assert len(conditions) == 1

        self.devices_page.select_query_field(self.devices_page.FIELD_IPS, conditions[0])
        self.devices_page.select_query_comp_op(COMP_CONTAINS, conditions[0])
        self.devices_page.fill_query_string_value(self.DEVICE_IP_PREFIX, conditions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 6
        return expressions, conditions

    def test_query_child_expression_not(self):
        self.prepare_to_query()
        expressions, conditions = self._prepare_child_expression()
        self.devices_page.toggle_not(conditions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 18

        self.devices_page.add_query_child_condition(expressions[0])
        conditions = self.devices_page.find_conditions(expressions[0])
        assert self.devices_page.is_query_error()
        assert len(conditions) == 2

        self.devices_page.select_query_field(self.devices_page.FIELD_MAC, conditions[1])
        self.devices_page.select_query_comp_op(COMP_CONTAINS, conditions[1])
        self.devices_page.fill_query_string_value(DEVICE_MAC, conditions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 1

        self.devices_page.toggle_not(conditions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 0

        self.devices_page.fill_query_string_value(self.IP_FRACTION, conditions[0])
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 1
        self.devices_page.toggle_not(conditions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 1

        self.devices_page.remove_query_expression(conditions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        conditions = self.devices_page.find_conditions(expressions[0])
        assert len(conditions) == 1
        assert len(self.devices_page.get_all_data()) == 1

        self.devices_page.toggle_not(conditions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()

    def test_query_child_expression_brackets_and_or(self):
        self.prepare_to_query()
        expressions, conditions = self._prepare_child_expression()

        self.devices_page.add_query_child_condition(expressions[0])
        self.devices_page.add_query_child_condition(expressions[0])
        time.sleep(1)
        conditions = self.devices_page.find_conditions(expressions[0])
        assert self.devices_page.is_query_error()
        assert len(conditions) == 3

        self.devices_page.select_query_field(self.devices_page.FIELD_MAC, conditions[1])
        self.devices_page.select_query_comp_op(COMP_EXISTS, conditions[1])
        self.devices_page.wait_for_table_to_be_responsive()

        self.devices_page.select_query_field(self.devices_page.FIELD_MAC, conditions[2])
        self.devices_page.select_query_comp_op(COMP_EXISTS, conditions[2])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 0
        self.devices_page.select_query_logic_op(LOGIC_OR, conditions[2])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 1

        self.devices_page.toggle_not(conditions[2])
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.is_query_error()

        self.devices_page.toggle_left_bracket(conditions[1])
        assert self.devices_page.is_query_error(self.ERROR_TEXT_QUERY_BRACKET.format(direction='right'))
        self.devices_page.toggle_right_bracket(conditions[2])
        assert self.devices_page.is_query_error()
        assert len(self.devices_page.get_all_data()) == 6

        self.devices_page.remove_query_expression(conditions[1])
        assert self.devices_page.is_query_error(self.ERROR_TEXT_QUERY_BRACKET.format(direction='left'))
        conditions = self.devices_page.find_conditions(expressions[0])
        self.devices_page.toggle_right_bracket(conditions[1])
        assert self.devices_page.is_query_error()
