from ui_tests.tests.ui_test_base import TestBase


class TestEntitiesTable(TestBase):
    QUERY_FIELDS = 'adapters,specific_data.data.hostname,specific_data.data.name,specific_data.data.last_seen,' \
                   'specific_data.data.os.type,specific_data.data.network_interfaces.ips,' \
                   'specific_data.data.network_interfaces.mac,labels'

    @staticmethod
    def check_toggle_advanced_basic(entities_page, entities_filter, tab_title, expected_advanced_text,
                                    expected_basic_text):
        entities_page.switch_to_page()
        entities_page.fill_filter(entities_filter)
        entities_page.enter_search()
        entities_page.wait_for_table_to_load()
        entities_page.click_row()
        entities_page.click_tab(tab_title)
        entities_page.click_advanced_view()
        assert entities_page.find_element_by_text(expected_advanced_text)
        entities_page.click_basic_view()
        assert entities_page.find_element_by_text(expected_basic_text)

    def check_initial_column_order(self, entities_page):
        entities_page.switch_to_page()
        self.base_page.run_discovery()
        assert entities_page.get_columns_header_text() == entities_page.get_displayed_columns_in_menu()
