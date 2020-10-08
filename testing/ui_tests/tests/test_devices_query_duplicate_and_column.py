import time

from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import (JSON_ADAPTER_NAME, COMP_EXISTS, LOGIC_OR)


class TestDevicesQueryDuplicateToggleColumn(TestBase):

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
                                        parent=all_expression_duplicate,
                                        button_selector=self.devices_page.EXPRESSION_TOGGLE_BUTTON)

    def test_complex_field_duplicate_and_toggle(self):
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()

        # Complex Field (OBJ)
        obj_expression = self.devices_page.add_query_expression()
        self.devices_page.assert_parent_toggle_column(parent=obj_expression, disabled=True, add=True)
        self.devices_page.select_context_obj(obj_expression)
        time.sleep(1.5)
        self.devices_page.select_query_field(self.devices_page.FIELD_NETWORK_INTERFACES, parent=obj_expression)
        conditions = self.devices_page.find_conditions(obj_expression)
        self.devices_page.select_query_field(self.devices_page.FIELD_MAC, conditions[0])
        self.devices_page.select_query_comp_op(COMP_EXISTS, conditions[0])
        conditions[0].find_element_by_css_selector(self.devices_page.CHILD_DUPLICATE_BUTTON).click()
        conditions = self.devices_page.find_conditions(obj_expression)
        assert conditions[0].text == conditions[1].text
        self.devices_page.select_query_field(self.devices_page.FIELD_IPS, conditions[1])
        self.devices_page.toggle_column(field=self.devices_page.FIELD_NETWORK_INTERFACES_MAC, exist_in_table=True,
                                        parent=conditions[0],
                                        button_selector=self.devices_page.CHILD_TOGGLE_BUTTON)
        obj_expression_duplicate = self.devices_page.duplicate_expression(obj_expression)
        assert obj_expression.text == obj_expression_duplicate.text

    def test_asset_entity_duplicate_and_toggle(self):
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()

        # Asset Entity (ENT)
        ent_expression = self.devices_page.add_query_expression()
        self.devices_page.select_context_ent(ent_expression)
        self.devices_page.select_asset_entity_adapter(ent_expression, JSON_ADAPTER_NAME)
        children = self.devices_page.get_asset_entity_children(ent_expression)
        self.devices_page.select_asset_entity_field(children[0], self.devices_page.FIELD_AVSTATUS)
        self.devices_page.select_query_comp_op(COMP_EXISTS, children[0])
        conditions = self.devices_page.find_conditions(ent_expression)
        self.devices_page.select_query_field(self.devices_page.FIELD_AVSTATUS, conditions[0])
        conditions[0].find_element_by_css_selector(self.devices_page.CHILD_DUPLICATE_BUTTON).click()
        conditions = self.devices_page.find_conditions(ent_expression)
        assert conditions[0].text == conditions[1].text
        self.devices_page.select_query_field(self.devices_page.FIELD_IPS, conditions[1])
        self.devices_page.assert_parent_toggle_column(parent=ent_expression, disabled=True, add=True)
        self.devices_page.toggle_column(field=self.devices_page.FIELD_AVSTATUS, exist_in_table=False,
                                        parent=conditions[0],
                                        button_selector=self.devices_page.CHILD_TOGGLE_BUTTON)
        ent_expression_duplicate = self.devices_page.duplicate_expression(ent_expression)
        assert ent_expression.text == ent_expression_duplicate.text

    def test_field_comparison_duplicate_and_toggle(self):
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.click_query_wizard()

        # Field Comparison (CMP)
        cmp_expression = self.devices_page.add_query_expression()
        self.devices_page.assert_parent_toggle_column(parent=cmp_expression, disabled=True, add=True)
        self.devices_page.select_query_logic_op(LOGIC_OR, parent=cmp_expression)
        self.devices_page.select_context_cmp(cmp_expression)
        self.devices_page.select_query_field(self.devices_page.FIELD_AVSTATUS, parent=cmp_expression)
        self.devices_page.toggle_column(field=self.devices_page.FIELD_AVSTATUS, exist_in_table=False,
                                        parent=cmp_expression,
                                        button_selector=self.devices_page.EXPRESSION_TOGGLE_BUTTON)
        cmp_expression_duplicate = self.devices_page.duplicate_expression(cmp_expression)
        assert cmp_expression.text == cmp_expression_duplicate.text
        self.devices_page.toggle_column(field=self.devices_page.FIELD_AVSTATUS, exist_in_table=True,
                                        parent=cmp_expression_duplicate,
                                        button_selector=self.devices_page.EXPRESSION_TOGGLE_BUTTON)
        self.devices_page.assert_parent_toggle_column(parent=cmp_expression, disabled=False, add=True)
