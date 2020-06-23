from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import (HOSTNAME_DC_QUERY, HOSTNAME_DC_QUERY_NAME,
                                      IPS_192_168_QUERY, IPS_192_168_QUERY_NAME)


class TestDashboardComparisonChart(TestBase):

    TEST_COMPARISON_TITLE = 'test comparison'

    def test_comparison_pie_total_values(self):
        self.devices_page.create_saved_query(IPS_192_168_QUERY, IPS_192_168_QUERY_NAME)
        self.devices_page.create_saved_query(HOSTNAME_DC_QUERY, HOSTNAME_DC_QUERY_NAME)

        self.base_page.run_discovery()
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_comparison_card([{'module': 'Devices', 'query': IPS_192_168_QUERY_NAME},
                                                 {'module': 'Devices', 'query': HOSTNAME_DC_QUERY_NAME}],
                                                title=self.TEST_COMPARISON_TITLE,
                                                chart_type='pie')

        self.dashboard_page.wait_for_spinner_to_end()
        pie = self.dashboard_page.get_card(self.TEST_COMPARISON_TITLE)
        slices_total_items = self.dashboard_page.get_pie_chart_slices_total_value(pie)
        footer_total_items = self.dashboard_page.get_pie_chart_footer_total_value(pie)
        assert slices_total_items == footer_total_items
        self.dashboard_page.remove_card(self.TEST_COMPARISON_TITLE)
