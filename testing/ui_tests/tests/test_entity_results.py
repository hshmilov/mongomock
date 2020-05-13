from services.adapters import csv_service
from test_credentials.test_csv_credentials import USERS_CLIENT_FILES
from ui_tests.tests.ui_consts import WINDOWS_QUERY_NAME, CSV_NAME, CSV_PLUGIN_NAME
from ui_tests.tests.ui_test_base import TestBase


class TestEntityResults(TestBase):
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
        entity_queries_page.run_query()
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

    def test_entities_table_adapter_order(self):
        csv = csv_service.CsvService()
        with csv.contextmanager(take_ownership=True):
            for position, client in enumerate(USERS_CLIENT_FILES, start=1):
                self.adapters_page.upload_csv(list(client.keys())[0], client, True)
                self.adapters_page.wait_for_server_green(position)
            self.dashboard_page.switch_to_page()
            self.base_page.run_discovery()
            self.users_page.switch_to_page()
            self.users_page.wait_for_table_to_load()
            self.users_page.run_filter_query('avidor')
            self.users_page.hover_over_entity_adapter_icon(index=0)
            adapters_popup_table_data = [x['Name'] for x in self.users_page.get_adapters_popup_table_data()]
            self.users_page.click_expand_row()
            adapters_expanded_data = self.users_page.get_column_data_adapter_title_tooltip()
            assert adapters_popup_table_data == adapters_expanded_data
            self.adapters_page.clean_adapter_servers(CSV_NAME)
        self.wait_for_adapter_down(CSV_PLUGIN_NAME)
