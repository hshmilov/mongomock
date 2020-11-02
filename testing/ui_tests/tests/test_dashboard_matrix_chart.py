from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import (MANAGED_DEVICES_QUERY_NAME, MANAGED_DEVICES_QUERY,
                                      DEVICES_NOT_SEEN_IN_LAST_30_DAYS_QUERY_NAME,
                                      DEVICES_SEEN_IN_LAST_7_DAYS_QUERY_NAME, DEVICES_SEEN_IN_LAST_7_DAYS_QUERY)


class TestDashboardMatrixChart(TestBase):
    MATRIX_CHART = 'Matrix Chart'
    MATRIX_CHART_1 = 'Matrix Chart 1'
    MATRIX_CHART_2 = 'Matrix Chart 2'
    MATRIX_CHART_3 = 'Matrix Chart 3'
    MATRIX_CHART_4 = 'Matrix Chart 4'

    DEVICES_SEEN_IN_LAST_7_DAYS_INTERSECTING_QUERY = \
        f'({MANAGED_DEVICES_QUERY}) and ({DEVICES_SEEN_IN_LAST_7_DAYS_QUERY})'

    def _verify_tooltip_and_get_percentage(self, card, item_title_text):
        assert self.dashboard_page.get_tooltip_header_name(card) == item_title_text
        assert self.dashboard_page.get_tooltip_body_name(card) != ''
        assert self.dashboard_page.get_tooltip_body_value(card) != ''
        return self.dashboard_page.get_tooltip_body_percentage(card)

    def _verify_group_tooltips(self, card, group_slices, expected_title):
        total_percentage = 0
        for index, curr_slice in enumerate(group_slices):
            self.dashboard_page.hover_over_element(curr_slice)
            total_percentage += self._verify_tooltip_and_get_percentage(card, expected_title)

        assert total_percentage == 100.0

    def _verify_sort_by_name(self, card, is_descending=True):
        group_names = self.dashboard_page.get_matrix_chart_group_names(card)
        self._verify_sort(group_names, is_descending)

    def _verify_sort_by_value(self, card, is_descending=True):
        group_values = self.dashboard_page.get_matrix_chart_group_values(card)
        self._verify_sort(group_values, is_descending)

    @staticmethod
    def _verify_sort(group_data, is_descending=True):
        group_data_sorted = group_data.copy()
        group_data_sorted.sort(reverse=is_descending)
        assert group_data == group_data_sorted

    def test_matrix_chart_groups(self):
        base_queries = [MANAGED_DEVICES_QUERY_NAME, MANAGED_DEVICES_QUERY_NAME,
                        DEVICES_SEEN_IN_LAST_7_DAYS_QUERY_NAME, None]
        intersecting_queries = [DEVICES_NOT_SEEN_IN_LAST_30_DAYS_QUERY_NAME, DEVICES_SEEN_IN_LAST_7_DAYS_QUERY_NAME]
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        card = self.dashboard_page.add_matrix_card('Devices', self.MATRIX_CHART, base_queries, intersecting_queries,
                                                   'name', 'desc')
        group_names = self.dashboard_page.get_matrix_chart_group_names(card)
        group_values = self.dashboard_page.get_matrix_chart_group_values(card)
        group_number = len(group_names)
        assert group_number == 4

        total_value = 0
        for index in range(0, group_number):
            group_name = group_names[index]
            if base_queries[index] is not None:
                assert group_name == base_queries[index]
            else:
                assert group_name == 'All devices'

            total_value += group_values[index]

            group_slices = self.dashboard_page.get_matrix_chart_group_slices(card, index)
            self._verify_group_tooltips(card, group_slices, group_name)

        assert self.dashboard_page.get_matrix_chart_total_value(card) == f'Total {total_value}'

    def test_matrix_chart_pagination(self):
        base_queries = [None, MANAGED_DEVICES_QUERY_NAME, MANAGED_DEVICES_QUERY_NAME,
                        MANAGED_DEVICES_QUERY_NAME, MANAGED_DEVICES_QUERY_NAME, MANAGED_DEVICES_QUERY_NAME]
        intersecting_queries = [DEVICES_NOT_SEEN_IN_LAST_30_DAYS_QUERY_NAME]
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        card = self.dashboard_page.add_matrix_card('Devices', self.MATRIX_CHART, base_queries, intersecting_queries)
        groups_names = self.dashboard_page.get_matrix_chart_group_names(card)
        assert len(groups_names) == 5
        assert self.dashboard_page.get_paginator_total_num_of_items(card) == '6'
        self.dashboard_page.get_next_page_button_in_paginator(card).click()
        groups_names = self.dashboard_page.get_matrix_chart_group_names(card)
        assert len(groups_names) == 1

    def test_matrix_chart_click(self):
        base_queries = [None, MANAGED_DEVICES_QUERY_NAME]
        intersecting_queries = [DEVICES_SEEN_IN_LAST_7_DAYS_QUERY_NAME, DEVICES_NOT_SEEN_IN_LAST_30_DAYS_QUERY_NAME]
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        card = self.dashboard_page.add_matrix_card('Devices', self.MATRIX_CHART, base_queries, intersecting_queries)
        self.dashboard_page.get_matrix_chart_group_slices(card, 0)[0].click()
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.find_search_value() == DEVICES_SEEN_IN_LAST_7_DAYS_QUERY
        self.dashboard_page.switch_to_page()
        card = self.dashboard_page.add_matrix_card('Devices', self.MATRIX_CHART, base_queries, intersecting_queries)
        self.dashboard_page.get_matrix_chart_group_slices(card, 1)[0].click()
        self.devices_page.wait_for_table_to_be_responsive()
        assert self.devices_page.find_search_value() == self.DEVICES_SEEN_IN_LAST_7_DAYS_INTERSECTING_QUERY

    def test_matrix_chart_sort_initial(self):
        base_queries = [None, MANAGED_DEVICES_QUERY_NAME, DEVICES_SEEN_IN_LAST_7_DAYS_QUERY_NAME]
        intersecting_queries = [DEVICES_NOT_SEEN_IN_LAST_30_DAYS_QUERY_NAME, DEVICES_SEEN_IN_LAST_7_DAYS_QUERY_NAME]
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        card = self.dashboard_page.add_matrix_card('Devices', self.MATRIX_CHART_1, base_queries, intersecting_queries,
                                                   'value', 'asc')
        self._verify_sort_by_value(card, False)
        card = self.dashboard_page.add_matrix_card('Devices', self.MATRIX_CHART_2, base_queries, intersecting_queries)
        self._verify_sort_by_value(card)
        card = self.dashboard_page.add_matrix_card('Devices', self.MATRIX_CHART_3, base_queries, intersecting_queries,
                                                   'name', 'asc')
        self._verify_sort_by_name(card, False)
        card = self.dashboard_page.add_matrix_card('Devices', self.MATRIX_CHART_4, base_queries, intersecting_queries,
                                                   'name', 'desc')
        self._verify_sort_by_name(card)

    def test_matrix_chart_sort_action(self):
        base_queries = [None, MANAGED_DEVICES_QUERY_NAME, DEVICES_SEEN_IN_LAST_7_DAYS_QUERY_NAME]
        intersecting_queries = [DEVICES_NOT_SEEN_IN_LAST_30_DAYS_QUERY_NAME, DEVICES_SEEN_IN_LAST_7_DAYS_QUERY_NAME]
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        card = self.dashboard_page.add_matrix_card('Devices', self.MATRIX_CHART_1, base_queries, intersecting_queries,
                                                   'value', 'asc')
        self.dashboard_page.select_chart_sort(card, 'value', 'desc')
        self._verify_sort_by_value(card)
        self.dashboard_page.select_chart_sort(card, 'value', 'asc')
        self._verify_sort_by_value(card, False)
        self.dashboard_page.select_chart_sort(card, 'name', 'desc')
        self._verify_sort_by_name(card)
        self.dashboard_page.select_chart_sort(card, 'name', 'asc')
        self._verify_sort_by_name(card, False)
