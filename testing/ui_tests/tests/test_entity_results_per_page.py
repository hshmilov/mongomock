from ui_tests.tests.ui_consts import WINDOWS_QUERY_NAME
from ui_tests.tests.ui_test_base import TestBase


class TestEntityResultsPerPage(TestBase):
    TWENTY_RESULTS_PER_PAGE = '20'
    FIFTY_RESULTS_PER_PAGE = '50'
    HUNDRED_RESULTS_PER_PAGE = '100'

    def change_count_entities_per_page(self, val):
        self.settings_page.switch_to_page()
        self.settings_page.click_gui_settings()
        self.settings_page.wait_for_spinner_to_end()
        self.settings_page.select_values_count_entities_per_column(val)
        self.settings_page.click_save_gui_settings()
        self.settings_page.wait_for_saved_successfully_toaster()

    def _test_count_entities_per_page(self, entities_page, entity_queries_page, query_name, query_filter):
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()
        assert entities_page.find_active_page_size() == self.TWENTY_RESULTS_PER_PAGE
        self.change_count_entities_per_page(self.HUNDRED_RESULTS_PER_PAGE)
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()
        assert entities_page.find_active_page_size() == self.HUNDRED_RESULTS_PER_PAGE

        entities_page.select_page_size(self.FIFTY_RESULTS_PER_PAGE)
        entities_page.create_saved_query(query_filter, query_name)
        entities_page.reset_query()
        assert entities_page.find_active_page_size() == self.FIFTY_RESULTS_PER_PAGE

        entities_page.select_page_size(self.TWENTY_RESULTS_PER_PAGE)
        entities_page.execute_saved_query(query_name)
        # Saved views ignore the page size so set value remains
        assert entities_page.find_active_page_size() == self.TWENTY_RESULTS_PER_PAGE

        entities_page.refresh()
        entities_page.wait_for_table_to_load()
        assert entities_page.find_active_page_size() == self.HUNDRED_RESULTS_PER_PAGE
        entity_queries_page.switch_to_page()
        entity_queries_page.wait_for_table_to_load()
        entity_queries_page.wait_for_spinner_to_end()
        # Verify this table is not influenced by count entities value
        assert entity_queries_page.find_active_page_size() == self.TWENTY_RESULTS_PER_PAGE
        query_row = entity_queries_page.find_query_row_by_name(query_name)
        query_row.click()
        entities_page.wait_for_table_to_load()
        assert entities_page.find_active_page_size() == self.HUNDRED_RESULTS_PER_PAGE

        # Reset 'defaultNumOfEntitiesPerPage' to default
        self.change_count_entities_per_page(self.TWENTY_RESULTS_PER_PAGE)

    def test_change_values_count_entities_per_page(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()

        self._test_count_entities_per_page(self.devices_page,
                                           self.devices_queries_page,
                                           WINDOWS_QUERY_NAME,
                                           self.devices_page.FILTER_OS_WINDOWS)

        self._test_count_entities_per_page(self.users_page,
                                           self.users_queries_page,
                                           self.users_page.ADMIN_QUERY_NAME,
                                           self.users_page.FILTER_IS_ADMIN)
