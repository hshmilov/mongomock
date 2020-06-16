import math

import pytest

from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import (OS_TYPE_OPTION_NAME, HOSTNAME_DC_QUERY, HOSTNAME_DC_QUERY_NAME,
                                      IPS_192_168_QUERY, IPS_192_168_QUERY_NAME,
                                      DEVICES_MODULE, MANAGED_DEVICES_QUERY_NAME, MANAGED_DEVICES_QUERY)


class TestDashboardCardLegend(TestBase):

    TEST_COMPARISON_TITLE = 'test comparison'
    TEST_SEGMENTATION_TITLE = 'test segmentation'
    TEST_INTERSECTION_TITLE = 'test intersection'

    SEGMENTATION_QUERY_SEARCH_TEXT = 'specific_data.data.os.type == "Windows"'
    INTERSECTION_QUERY_SEARCH_TEXT = 'not ((specific_data.data.network_interfaces.ips == regex("192.168", "i")) ' \
                                     'or (specific_data.data.hostname == regex("dc", "i")))'

    def _test_pie_chart_legend_click(self, legend_grid_rows, expected_query):
        legend_grid_rows[0]['name_element'].click()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_search_value() == expected_query

    def _test_legend_grid_rows(self, legend_grid_rows, item_titles):
        total_percentage = 0
        for index, grid_row_data in enumerate(legend_grid_rows):
            assert grid_row_data['name'] == item_titles[math.floor(index)]
            assert grid_row_data['value'] != ''
            assert grid_row_data['percentage'] != ''
            total_percentage += self.dashboard_page.get_percentage_number(grid_row_data['percentage'])
        assert total_percentage == 100

    def _test_pie_chart_legend(self, card_title, expected_query, item_titles):
        card = self.dashboard_page.get_card(card_title)
        self.dashboard_page.click_legend_toggle(card)
        legend_grid_rows = self.dashboard_page.get_pie_chart_legend_rows_data(card)
        self._test_legend_grid_rows(legend_grid_rows, item_titles)
        self._test_pie_chart_legend_click(legend_grid_rows, expected_query)

    @pytest.mark.skip('ad change')
    def test_pie_chart_legend_toggle(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        module_query_list = [{'module': DEVICES_MODULE, 'query': MANAGED_DEVICES_QUERY_NAME}] * 5
        self.dashboard_page.add_comparison_card(
            module_query_list, title=self.TEST_COMPARISON_TITLE, chart_type='pie')
        card = self.dashboard_page.get_card(self.TEST_COMPARISON_TITLE)

        # verify that click opens legend
        self.dashboard_page.verify_legend_absent(card)
        self.dashboard_page.click_legend_toggle(card)
        self.dashboard_page.get_legend(card)

        # verify that 2nd click hides legend
        self.dashboard_page.click_legend_toggle(card)
        self.dashboard_page.verify_legend_absent(card)

        # verify that menu click closes legend
        self.dashboard_page.click_legend_toggle(card)
        self.dashboard_page.get_legend(card)
        self.dashboard_page.edit_card(self.TEST_COMPARISON_TITLE)
        self.dashboard_page.verify_legend_absent(card)

    @pytest.mark.skip('ad change')
    def test_comparison_pie_chart_legend(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        module_query_list = [{'module': DEVICES_MODULE, 'query': MANAGED_DEVICES_QUERY_NAME}] * 5
        self.dashboard_page.add_comparison_card(
            module_query_list, title=self.TEST_COMPARISON_TITLE, chart_type='pie')
        self._test_pie_chart_legend(self.TEST_COMPARISON_TITLE,
                                    MANAGED_DEVICES_QUERY, [MANAGED_DEVICES_QUERY_NAME] * 5)

    @pytest.mark.skip('ad change')
    def test_segmentation_pie_chart_legend(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_segmentation_card(
            'Devices', OS_TYPE_OPTION_NAME, self.TEST_SEGMENTATION_TITLE, 'pie')
        self._test_pie_chart_legend(self.TEST_SEGMENTATION_TITLE,
                                    self.SEGMENTATION_QUERY_SEARCH_TEXT, ['Windows', 'No Value'])

    def test_intersection_pie_chart_legend(self):
        self.devices_page.create_saved_query(IPS_192_168_QUERY, IPS_192_168_QUERY_NAME)
        self.devices_page.create_saved_query(HOSTNAME_DC_QUERY, HOSTNAME_DC_QUERY_NAME)
        self.base_page.run_discovery()
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_intersection_card(DEVICES_MODULE,
                                                  IPS_192_168_QUERY_NAME,
                                                  HOSTNAME_DC_QUERY_NAME,
                                                  self.TEST_INTERSECTION_TITLE)
        self.dashboard_page.wait_for_spinner_to_end()

        card = self.dashboard_page.get_card(self.TEST_INTERSECTION_TITLE)
        self.dashboard_page.click_legend_toggle(card)
        legend_grid_rows = self.dashboard_page.get_pie_chart_legend_rows_data(card)
        self._test_legend_grid_rows(legend_grid_rows,
                                    ['Excluding', 'IPs Subnet 192.168.0.0',
                                     'IPs Subnet 192.168.0.0 + DC Devices', 'DC Devices'])
        self._test_pie_chart_legend_click(legend_grid_rows, self.INTERSECTION_QUERY_SEARCH_TEXT)
