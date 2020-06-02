import pytest

from ui_tests.tests.ui_consts import USERS_MODULE, IS_ADMIN_OPTION_NAME, JSON_ADAPTER_NAME, AD_ADAPTER_NAME
from ui_tests.tests.ui_test_base import TestBase


# pylint: disable=no-member


class TestDashboardChartsData(TestBase):
    CARD_TITLE = 'segmentation filter test'

    @pytest.mark.skip('ad change')
    def test_segmentation_chart_data_from_adapter(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_segmentation_card(module=USERS_MODULE,
                                                  field=IS_ADMIN_OPTION_NAME,
                                                  title=self.CARD_TITLE,
                                                  include_empty=False)
        card = self.dashboard_page.find_dashboard_card(self.CARD_TITLE)
        self.dashboard_page.assert_histogram_lines_data(card, ['13', '3'])
        with self.dashboard_page.edit_and_assert_chart(card, ['1', '1'],
                                                       self.dashboard_page.HISTOGRAM_CHART_TYPE):
            self.dashboard_page.select_chart_wizard_adapter(JSON_ADAPTER_NAME)

        with self.dashboard_page.edit_and_assert_chart(card, ['13', '2'],
                                                       self.dashboard_page.HISTOGRAM_CHART_TYPE):
            self.dashboard_page.select_chart_wizard_adapter(AD_ADAPTER_NAME)

        with self.dashboard_page.edit_and_assert_chart(card, ['13'],
                                                       self.dashboard_page.HISTOGRAM_CHART_TYPE):
            self.dashboard_page.fill_chart_segment_filter(IS_ADMIN_OPTION_NAME, 'false')
