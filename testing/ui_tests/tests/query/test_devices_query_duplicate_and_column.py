import time

from ui_tests.tests.query.query_test_base import QueryTestBase
from ui_tests.tests.ui_consts import (JSON_ADAPTER_NAME, COMP_EXISTS)


class TestDevicesQueryDuplicateToggleColumn(QueryTestBase):

    def test_aggregated_data_duplicate_and_toggle(self):
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()

        # Aggregated Data (ALL)
        all_expression = self.devices_page.find_expressions()[0]
        self.devices_page.assert_parent_toggle_column(parent=all_expression, disabled=True, add=True)
        self.devices_page.toggle_left_bracket(all_expression)
        self.devices_page.toggle_not(all_expression)
        self.devices_page.select_context_all(all_expression)
        self.devices_page.select_query_field(self.devices_page.FIELD_SAVED_QUERY, parent=all_expression)
        self.devices_page.toggle_right_bracket(all_expression)
        self.devices_page.assert_parent_toggle_column(parent=all_expression, disabled=True, add=True)

        all_expression_duplicate = self.devices_page.duplicate_expression(all_expression)
        self.devices_page.assert_context_all(all_expression_duplicate)
        assert self.devices_page.is_left_bracket_on(all_expression_duplicate)
        assert self.devices_page.is_right_bracket_on(all_expression_duplicate)
        assert self.devices_page.is_expression_not_on(all_expression_duplicate)
        assert self.devices_page.is_logic_op_equals_to_and(all_expression_duplicate)
        self.devices_page.select_query_field(self.devices_page.FIELD_HOSTNAME_TITLE, parent=all_expression_duplicate)
        self.devices_page.toggle_column(field=self.devices_page.FIELD_HOSTNAME_TITLE, exist_in_table=True,
                                        parent=all_expression_duplicate)

    def test_complex_field_duplicate_and_toggle(self):
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()

        # Complex Field (OBJ)
        expressions = self.devices_page.find_expressions()
        self.devices_page.assert_parent_toggle_column(parent=expressions[0], disabled=True, add=True)
        self.devices_page.select_context_obj(expressions[0])
        time.sleep(1.5)
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES, parent=expressions[0])
        conditions = self.devices_page.find_conditions(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_MAC, conditions[0])
        self.devices_page.select_query_comp_op(COMP_EXISTS, conditions[0])

        self._assert_condition_duplication(expressions[0], conditions[0])
        conditions = self.devices_page.find_conditions(expressions[0])

        self.devices_page.select_query_field(self.devices_page.FIELD_IPS, conditions[1])
        self.devices_page.toggle_column(field=self.devices_page.FIELD_NETWORK_INTERFACES_MAC, exist_in_table=True,
                                        parent=conditions[0])

        self._assert_expression_duplication()

    def test_asset_entity_duplicate_and_toggle(self):
        self.prepare_to_query()

        # Asset Entity (ENT)
        expressions = self.devices_page.find_expressions()
        self.devices_page.select_context_ent(expressions[0])
        self.devices_page.select_asset_entity_adapter(expressions[0], JSON_ADAPTER_NAME)
        conditions = self.devices_page.find_conditions(expressions[0])
        self.devices_page.select_asset_entity_field(conditions[0], self.devices_page.FIELD_AVSTATUS)
        self.devices_page.select_query_comp_op(COMP_EXISTS, conditions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_AVSTATUS, conditions[0])

        self._assert_condition_duplication(expressions[0], conditions[0])
        conditions = self.devices_page.find_conditions(expressions[0])

        self.devices_page.select_query_field(self.devices_page.FIELD_IPS, conditions[1])
        self.devices_page.assert_parent_toggle_column(parent=expressions[0], disabled=True, add=True)
        self.devices_page.toggle_column(field=self.devices_page.FIELD_AVSTATUS, exist_in_table=False,
                                        parent=conditions[0])

        self._assert_expression_duplication()

    def test_field_comparison_duplicate_and_toggle(self):
        self.prepare_to_query()

        # Field Comparison (CMP)
        expressions = self.devices_page.find_expressions()
        self.devices_page.assert_parent_toggle_column(parent=expressions[0], disabled=True, add=True)
        self.devices_page.select_context_cmp(expressions[0])
        self.devices_page.select_query_field(self.devices_page.FIELD_AVSTATUS, parent=expressions[0])
        self.devices_page.toggle_column(field=self.devices_page.FIELD_AVSTATUS, exist_in_table=False,
                                        parent=expressions[0])
        self._assert_expression_duplication()
        expressions = self.devices_page.find_expressions()
        self.devices_page.toggle_column(field=self.devices_page.FIELD_AVSTATUS, exist_in_table=True,
                                        parent=expressions[1])
        self.devices_page.assert_parent_toggle_column(parent=expressions[1], disabled=False, add=True)

    def _assert_condition_duplication(self, expression, condition):
        self.devices_page.duplicate_condition(condition)
        self.devices_page.duplicate_condition(condition)
        conditions = self.devices_page.find_conditions(expression)
        assert conditions[1].text == conditions[2].text

    def _assert_expression_duplication(self):
        expressions = self.devices_page.find_expressions()
        self.devices_page.duplicate_expression(expressions[0])
        self.devices_page.duplicate_expression(expressions[0])
        expressions = self.devices_page.find_expressions()
        assert expressions[1].text == expressions[2].text
