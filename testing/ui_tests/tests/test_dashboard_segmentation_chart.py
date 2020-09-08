from ui_tests.tests.test_dashboard_chart_base import TestDashboardChartBase
from ui_tests.tests.ui_consts import (OS_TYPE_OPTION_NAME)


class TestDashboardSegmentationChart(TestDashboardChartBase):

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

    def test_check_segmentation_csv(self):
        histogram_items_title = []
        chart = \
            self.dashboard_page.create_and_get_paginator_segmentation_card(
                run_discovery=True,
                module='Devices',
                field='Host Name',
                title=self.TEST_SEGMENTATION_TITLE,
                view_name='')
        histogram_card = chart.get('card')

        num_of_pages = self.dashboard_page.get_last_page_button_in_paginator(histogram_card)

        histogram_card = self.dashboard_page.get_card(card_title=self.TEST_SEGMENTATION_TITLE)
        histograms_chart = self.dashboard_page.get_histogram_chart_from_card(card=histogram_card)
        histogram_items_title.append(self.dashboard_page.get_histogram_current_page_item_titles(histograms_chart))
        self.dashboard_page.click_to_next_page(histogram_card)
        self.dashboard_page.wait_for_card_spinner_to_end()

        # iterate incrementaly on all the pages (next)
        for page_number in range(1, num_of_pages):
            histogram_card = self.dashboard_page.get_card(card_title=self.TEST_SEGMENTATION_TITLE)
            histograms_chart = self.dashboard_page.get_histogram_chart_from_card(card=histogram_card)
            histogram_items_title.append(self.dashboard_page.get_histogram_current_page_item_titles(histograms_chart))

            if page_number == num_of_pages:
                break
            else:
                self.dashboard_page.click_to_next_page(histogram_card)
                self.dashboard_page.wait_for_card_spinner_to_end()

        # flatten list
        histogram_titles_list = [item for sublist in histogram_items_title for item in sublist]
        csv_data = self._download_and_get_csv(self.TEST_SEGMENTATION_TITLE)
        host_names_list = [x[0] for x in csv_data]
        # compare histograms_item_titles of pagination with data grabbed from devices table
        self.dashboard_page.assert_data_devices_fit_pagination_data(histogram_titles_list, host_names_list)
        self.dashboard_page.remove_card(self.TEST_SEGMENTATION_TITLE)
