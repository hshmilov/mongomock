from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import QueriesScreen


class TestSavedQuery(TestBase):
    def test_saved_query(self):
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_be_responsive()

        self.devices_queries_page.fill_enter_table_search(QueriesScreen.query_1_name)
        self.devices_queries_page.wait_for_table_to_be_responsive()

        assert self.devices_queries_page.find_query_row_by_name(QueriesScreen.query_1_name)
