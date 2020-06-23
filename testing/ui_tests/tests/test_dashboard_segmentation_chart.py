from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import (OS_TYPE_OPTION_NAME)


class TestDashboardSegmentationChart(TestBase):

    TEST_SEGMENTATION_TITLE = 'test segmentation'

    def test_segmentation_pie_total_values(self):
        self.base_page.run_discovery()
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_segmentation_card('Devices', OS_TYPE_OPTION_NAME, self.TEST_SEGMENTATION_TITLE, 'pie')

        self.dashboard_page.wait_for_spinner_to_end()
        pie = self.dashboard_page.get_card(self.TEST_SEGMENTATION_TITLE)
        slices_total_items = self.dashboard_page.get_pie_chart_slices_total_value(pie)
        footer_total_items = self.dashboard_page.get_pie_chart_footer_total_value(pie)
        assert slices_total_items == footer_total_items
        self.dashboard_page.remove_card(self.TEST_SEGMENTATION_TITLE)
