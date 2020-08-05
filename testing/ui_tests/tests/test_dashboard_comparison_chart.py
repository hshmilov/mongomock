from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import (HOSTNAME_DC_QUERY, HOSTNAME_DC_QUERY_NAME,
                                      IPS_192_168_QUERY, IPS_192_168_QUERY_NAME, DEVICES_MODULE,
                                      AD_MISSING_AGENTS_QUERY_NAME, MANAGED_DEVICES_QUERY_NAME, MANAGED_DEVICES_QUERY)


class TestDashboardComparisonChart(TestBase):

    TEST_COMPARISON_TITLE = 'test comparison'

    def test_comparison_pie_total_values(self):
        self.devices_page.create_saved_query(IPS_192_168_QUERY, IPS_192_168_QUERY_NAME)
        self.devices_page.create_saved_query(HOSTNAME_DC_QUERY, HOSTNAME_DC_QUERY_NAME)

        self.base_page.run_discovery()
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_comparison_card([{'module': DEVICES_MODULE, 'query': IPS_192_168_QUERY_NAME},
                                                 {'module': DEVICES_MODULE, 'query': HOSTNAME_DC_QUERY_NAME}],
                                                title=self.TEST_COMPARISON_TITLE,
                                                chart_type='pie')

        self.dashboard_page.wait_for_spinner_to_end()
        pie = self.dashboard_page.get_card(self.TEST_COMPARISON_TITLE)
        slices_total_items = self.dashboard_page.get_pie_chart_slices_total_value(pie)
        footer_total_items = self.dashboard_page.get_pie_chart_footer_total_value(pie)
        assert slices_total_items == footer_total_items
        self.dashboard_page.remove_card(self.TEST_COMPARISON_TITLE)

    def test_comparison_saves_query_link(self):
        self.base_page.run_discovery()
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_comparison_card([{'module': DEVICES_MODULE, 'query': AD_MISSING_AGENTS_QUERY_NAME},
                                                 {'module': DEVICES_MODULE, 'query': MANAGED_DEVICES_QUERY_NAME}],
                                                self.TEST_COMPARISON_TITLE)

        self.dashboard_page.wait_for_spinner_to_end()
        card = self.dashboard_page.get_card(self.TEST_COMPARISON_TITLE)
        line = self.dashboard_page.get_histogram_line_from_histogram(card, 1)
        line.click()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_query_title_text() == MANAGED_DEVICES_QUERY_NAME
        assert self.devices_page.get_query_search_input_value() == MANAGED_DEVICES_QUERY
        self.dashboard_page.switch_to_page()
        self.dashboard_page.remove_card(self.TEST_COMPARISON_TITLE)
