from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import (OS_TYPE_OPTION_NAME, HOSTNAME_DC_QUERY, HOSTNAME_DC_QUERY_NAME,
                                      IPS_192_168_QUERY, IPS_192_168_QUERY_NAME,
                                      DEVICES_MODULE, MANAGED_DEVICES_QUERY_NAME)


class TestDashboardCardTooltip(TestBase):

    TEST_COMPARISON_TITLE = 'test comparison'
    TEST_SEGMENTATION_TITLE = 'test segmentation'
    TEST_INTERSECTION_TITLE = 'test intersection'

    DEVICES_QUERY = {'module': DEVICES_MODULE, 'query': MANAGED_DEVICES_QUERY_NAME}

    def _verify_histogram_tooltip_and_get_percentage(self, card, item_title, item_value):
        assert self.dashboard_page.get_tooltip_title(card) == item_title
        assert self.dashboard_page.get_tooltip_body_value(card) == item_value
        return self.dashboard_page.get_tooltip_body_percentage(card)

    def _test_histogram_tooltip(self, card_title):
        card = self.dashboard_page.get_card(card_title)
        histogram = self.dashboard_page.get_histogram_chart_from_card(card)

        histogram_item_titles = self.dashboard_page.get_histogram_current_page_item_titles(histogram)
        total_percentage = 0
        for index, title in enumerate(histogram_item_titles, 1):
            value = self.dashboard_page.get_histogram_line_from_histogram(histogram, index).text
            self.dashboard_page.hover_over_histogram_bar(histogram, index)
            total_percentage += self._verify_histogram_tooltip_and_get_percentage(card, title, value)

        assert total_percentage == 100.0

    def test_comparison_histogram_tooltip(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        module_query_list = [self.DEVICES_QUERY] * 5
        self.dashboard_page.add_comparison_card(
            module_query_list, title=self.TEST_COMPARISON_TITLE, chart_type='histogram')
        self._test_histogram_tooltip(self.TEST_COMPARISON_TITLE)

    def test_segmentation_histogram_tooltip(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_segmentation_card(
            'Devices', OS_TYPE_OPTION_NAME, self.TEST_SEGMENTATION_TITLE)
        self._test_histogram_tooltip(self.TEST_SEGMENTATION_TITLE)

    def _verify_pie_chart_tooltip_and_get_percentage(self, card):
        assert self.dashboard_page.get_tooltip_title(card) != ''
        assert self.dashboard_page.get_tooltip_body_value(card) != ''
        body_percentage = self.dashboard_page.get_tooltip_body_percentage(card)
        assert body_percentage != ''
        return body_percentage

    def _test_pie_chart_tooltip(self, card_title):
        card = self.dashboard_page.get_card(card_title)
        pie_chart = self.dashboard_page.get_pie_chart_from_card(card)
        pie_chart_slices = self.dashboard_page.get_pie_chart_slices(pie_chart)

        total_percentage = 0
        for index, current_slice in enumerate(pie_chart_slices):
            self.dashboard_page.hover_over_element(current_slice)
            total_percentage += self._verify_pie_chart_tooltip_and_get_percentage(card)

        assert total_percentage == 100.0

    def test_comparison_pie_chart_tooltip(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        module_query_list = [self.DEVICES_QUERY] * 5
        self.dashboard_page.add_comparison_card(
            module_query_list, title=self.TEST_COMPARISON_TITLE, chart_type='pie')
        self._test_pie_chart_tooltip(self.TEST_COMPARISON_TITLE)

    def test_segmentation_pie_chart_tooltip(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_segmentation_card(
            DEVICES_MODULE, 'Last Seen', self.TEST_SEGMENTATION_TITLE, 'pie', 'Devices not seen in last 30 days')
        self._test_pie_chart_tooltip(self.TEST_SEGMENTATION_TITLE)

    def test_intersection_pie_chart_tooltip(self):
        def _verify_excluding_or_intersection_tooltip():
            assert len(self.dashboard_page.get_tooltip_body_component_names(card)) > 0
            header_percentage = self.dashboard_page.get_tooltip_header_percentage(card)
            assert header_percentage != ''
            return header_percentage

        self.devices_page.create_saved_query(IPS_192_168_QUERY, IPS_192_168_QUERY_NAME)
        self.devices_page.create_saved_query(HOSTNAME_DC_QUERY, HOSTNAME_DC_QUERY_NAME)
        self.base_page.run_discovery()
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_intersection_card(DEVICES_MODULE,
                                                  IPS_192_168_QUERY_NAME,
                                                  HOSTNAME_DC_QUERY_NAME,
                                                  self.TEST_INTERSECTION_TITLE)
        card = self.dashboard_page.get_card(self.TEST_INTERSECTION_TITLE)
        pie_chart = self.dashboard_page.get_pie_chart_from_card(card)
        pie_chart_slices = self.dashboard_page.get_pie_chart_slices(pie_chart)

        excluding_slice_exists = False
        intersection_slice_exists = False
        total_percentage = 0

        for index, pie_chart_slice in enumerate(pie_chart_slices, 0):
            self.dashboard_page.hover_over_element(pie_chart_slices[index])
            tooltip_title = self.dashboard_page.get_tooltip_title(card)
            if tooltip_title == 'Excluding':
                excluding_slice_exists = True
                total_percentage += _verify_excluding_or_intersection_tooltip()
            elif tooltip_title == 'Intersection':
                intersection_slice_exists = True
                total_percentage += _verify_excluding_or_intersection_tooltip()
            else:
                total_percentage += self._verify_pie_chart_tooltip_and_get_percentage(card)

        assert excluding_slice_exists
        assert intersection_slice_exists
        assert total_percentage == 100
