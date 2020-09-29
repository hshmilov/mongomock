from ui_tests.tests.query.query_test_base import QueryTestBase
from ui_tests.tests.ui_consts import (COMP_DAYS, COMP_HOURS,
                                      COMP_NEXT_DAYS, COMP_NEXT_HOURS,
                                      AD_ADAPTER_NAME, JSON_ADAPTER_NAME,
                                      LOGIC_AND)


class TestQueryLastSeen(QueryTestBase):

    def _test_last_seen_query(self, query_comp=COMP_DAYS, query_value=365):
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[0])
        self.devices_page.select_query_comp_op(query_comp, parent=expressions[0])
        self.devices_page.fill_query_value(query_value, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        results_count = len(self.devices_page.get_all_data())
        self.devices_page.select_query_logic_op(LOGIC_AND)
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[1])
        self.devices_page.select_query_comp_op(query_comp, parent=expressions[1])
        self.devices_page.fill_query_value(1, parent=expressions[1])
        self.devices_page.wait_for_table_to_be_responsive()
        if query_comp in (COMP_DAYS, COMP_HOURS):
            assert len(self.devices_page.get_all_data()) < results_count
        else:
            assert len(self.devices_page.get_all_data()) == results_count
        self.devices_page.clear_query_wizard()

    def test_last_seen_query_days(self):
        self.prepare_to_query()
        self._test_last_seen_query(COMP_DAYS)
        self._test_last_seen_query(COMP_NEXT_DAYS)

    def test_last_seen_query_hours(self):
        self.prepare_to_query()
        self._test_last_seen_query(COMP_HOURS, 365 * 24)
        self._test_last_seen_query(COMP_NEXT_HOURS, 365 * 24)

    def test_last_seen_query_filter_adapters(self):
        self.prepare_to_query()
        self.devices_page.add_query_expression()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 2
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[0])
        self.devices_page.select_query_comp_op(COMP_DAYS, parent=expressions[0])
        self.devices_page.fill_query_value(365, parent=expressions[0])
        self.devices_page.wait_for_table_to_be_responsive()
        results_count = len(self.devices_page.get_all_data())
        self.devices_page.select_query_logic_op(LOGIC_AND)
        self.devices_page.click_on_select_all_filter_adapters(parent=expressions[1])
        self.devices_page.click_on_filter_adapter(AD_ADAPTER_NAME, parent=expressions[1])
        self.devices_page.select_query_field(self.devices_page.FIELD_LAST_SEEN, parent=expressions[1])
        self.devices_page.select_query_comp_op(COMP_DAYS, parent=expressions[1])
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
