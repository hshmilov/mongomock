from ui_tests.tests.ui_test_base import TestBase
from upgrade.consts import QueriesScreen


class TestSavedQuery(TestBase):
    def test_saved_query(self):
        self.devices_page.switch_to_page()
        self.devices_page.fill_filter(QueriesScreen.query_1)
        self.devices_page.enter_search()
        self.devices_page.click_save_query()
        self.devices_page.fill_query_name(QueriesScreen.query_1_name)
        self.devices_page.click_save_query_save_button()

        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_load()

        query_row = self.devices_queries_page.find_query_row_by_name(QueriesScreen.query_1_name)
        query_filter = self.devices_queries_page.find_query_filter_in_row(query_row)

        assert query_filter == QueriesScreen.query_1
