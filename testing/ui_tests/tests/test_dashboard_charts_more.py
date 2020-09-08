import time

import pytest
from selenium.common.exceptions import NoSuchElementException

from axonius.consts.gui_consts import DASHBOARD_SPACE_PERSONAL
from axonius.utils.wait import wait_until
from ui_tests.tests.test_dashboard_chart_base import TestDashboardChartBase
from ui_tests.tests.ui_consts import (LINUX_QUERY_NAME, OS_TYPE_OPTION_NAME,
                                      WINDOWS_QUERY_NAME)


class TestDashboardChartsMore(TestDashboardChartBase):
    TEST_MOVE_PANEL = 'test move panel'
    UNCOVERED_QUERY = 'not (((specific_data.data.adapter_properties == "Agent") or ' \
                      '(specific_data.data.adapter_properties == "Manager")))'
    COVERED_QUERY = '((specific_data.data.adapter_properties == "Agent") ' \
                    'or (specific_data.data.adapter_properties == "Manager"))'
    NO_OS_QUERY = 'not (specific_data.data.os.type == exists(true))'
    TEST_SEGMENTATION_PIE_TITLE = 'test segmentation pie'
    SEGMENTATION_PIE_CARD_QUERY = 'specific_data.data.hostname == '
    OS_WINDOWS_QUERY = 'specific_data.data.os.type == "Windows"'
    SUMMARY_CARD_QUERY_DEVICES = 'specific_data.data.hostname == exists(true)'
    TEST_SUMMARY_TITLE_USERS = 'test summary users'
    SUMMARY_CARD_QUERY_USERS = 'specific_data.data.logon_count == exists(true) and specific_data.data.logon_count > 0'

    def test_dashboard_empty_title(self):
        """
        Test empty dashboard card with no title, save won't be clickable (disabled) and will "fail" then we actually
        add title and save and it should work
        """
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, WINDOWS_QUERY_NAME)
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_LINUX, LINUX_QUERY_NAME)
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        with pytest.raises(NoSuchElementException):
            self.dashboard_page.add_comparison_card([{'module': 'Devices', 'query': WINDOWS_QUERY_NAME},
                                                     {'module': 'Devices', 'query': LINUX_QUERY_NAME}],
                                                    '')

        assert self.dashboard_page.is_chart_save_disabled()
        # this should work after we add the title
        self.dashboard_page.fill_current_chart_title(self.TEST_EDIT_CHART_TITLE)
        assert not self.dashboard_page.is_chart_save_disabled()
        self.dashboard_page.click_card_save()

    def test_dashboard_chart_move(self):
        card_title = self.TEST_MOVE_PANEL
        self.base_page.run_discovery()
        self.dashboard_page.switch_to_page()
        self.dashboard_page.wait_for_card_spinner_to_end()
        self.dashboard_page.add_summary_card('Devices', 'Host Name', 'Count', card_title)
        self.dashboard_page.wait_for_spinner_to_end()
        new_space_name = 'test space'
        self.dashboard_page.add_new_space(new_space_name)
        wait_until(lambda: self.dashboard_page.find_space_header_title(3) == new_space_name)
        self.dashboard_page.find_space_header(1).click()
        self.dashboard_page.open_move_or_copy_card(card_title)
        self.dashboard_page.select_space_for_move_or_copy(DASHBOARD_SPACE_PERSONAL)
        assert self.dashboard_page.is_move_or_copy_checkbox_disabled()
        self.dashboard_page.select_space_for_move_or_copy(new_space_name)
        self.dashboard_page.toggle_move_or_copy_checkbox()
        self.dashboard_page.click_button('OK')
        wait_until(lambda: self.dashboard_page.is_missing_panel(card_title))
        self.dashboard_page.find_space_header(3).click()
        last_card = self.dashboard_page.get_last_card_created()
        assert self.dashboard_page.get_title_from_card(last_card) == card_title
        self.dashboard_page.remove_card(card_title)

    def test_dashboard_coverage_chart(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()

        # Allow the caches to be rebuilt
        time.sleep(5)

        # This triggers a dashboard reload
        self.settings_page.switch_to_page()
        self.dashboard_page.switch_to_page()

        self.dashboard_page.click_uncovered_pie_slice()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_search_value() == self.UNCOVERED_QUERY
        self.devices_page.click_query_wizard()
        # make sure there is no error in the wizard
        assert self.devices_page.is_query_error()
        self.devices_page.click_search()
        self.dashboard_page.switch_to_page()
        self.dashboard_page.click_covered_pie_slice()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_search_value() == self.COVERED_QUERY
        self.devices_page.click_query_wizard()
        # make sure there is no error in the wizard
        assert self.devices_page.is_query_error()
        self.devices_page.click_search()

    def test_dashboard_intersection_chart_config_reset(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_intersection_card('Users', 'AD enabled locked users',
                                                  'AD disabled users', self.TEST_INTERSECTION_TITLE)
        self.dashboard_page.wait_for_spinner_to_end()
        # verify card config reset
        self.dashboard_page.verify_card_config_reset_intersection_chart(self.TEST_INTERSECTION_TITLE)
        self.dashboard_page.remove_card(self.TEST_INTERSECTION_TITLE)

    def test_dashboard_segmentation_chart(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_segmentation_card(
            'Devices', OS_TYPE_OPTION_NAME, self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        # verify config reset
        self.dashboard_page.verify_card_config_reset_segmentation_chart(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        shc_card = self.dashboard_page.get_card(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        shc_chart = self.dashboard_page.get_histogram_chart_from_card(shc_card)
        line = self.dashboard_page.get_histogram_line_from_histogram(shc_chart, 1)
        first_result_count = int(line.text)
        line.click()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == first_result_count
        if first_result_count == 1:
            assert self.devices_page.find_search_value() == self.NO_OS_QUERY
        else:
            assert self.devices_page.find_search_value() == self.OS_WINDOWS_QUERY
            self.dashboard_page.switch_to_page()
            shc_card = self.dashboard_page.get_card(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
            shc_chart = self.dashboard_page.get_histogram_chart_from_card(shc_card)
            line = self.dashboard_page.get_histogram_line_from_histogram(shc_chart, 2)
            second_result_count = int(line.text)
            line.click()
            self.devices_page.wait_for_table_to_load()
            assert self.devices_page.count_entities() == second_result_count
            assert self.devices_page.find_search_value() == self.NO_OS_QUERY
        self.dashboard_page.switch_to_page()
        self.dashboard_page.wait_for_spinner_to_end()
        self.dashboard_page.add_segmentation_card('Devices', 'Host Name', self.TEST_SEGMENTATION_PIE_TITLE, 'pie')
        self.dashboard_page.wait_for_spinner_to_end()
        self.dashboard_page.click_segmentation_pie_card(self.TEST_SEGMENTATION_PIE_TITLE)
        self.devices_page.wait_for_table_to_load()
        assert self.SEGMENTATION_PIE_CARD_QUERY in self.devices_page.find_search_value()
        assert self.devices_page.count_entities() == 1
        self.dashboard_page.switch_to_page()

        self._test_dashboard_segmentation_filter()
        self.dashboard_page.remove_card(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        self.dashboard_page.remove_card(self.TEST_SEGMENTATION_PIE_TITLE)

    def _test_dashboard_segmentation_filter(self):
        # Add empty values - expected to generate two bars (Windows and No Value)
        self.dashboard_page.edit_card(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        self.dashboard_page.check_chart_segment_include_empty()
        self.dashboard_page.click_card_save()
        filtered_chart = self.dashboard_page.get_card(card_title=self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        assert self.dashboard_page.get_paginator_total_num_of_items(filtered_chart) == '1'

        # Change to host and add filter 'domain' - expected to filter out the JSON device
        self.dashboard_page.edit_card(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        self.dashboard_page.check_chart_segment_include_empty()
        assert not self.dashboard_page.is_toggle_selected(self.dashboard_page.find_chart_segment_include_empty())
        self.dashboard_page.select_chart_wizard_field('Host Name')
        self.dashboard_page.fill_chart_segment_filter('Host Name', 'domain')
        self.dashboard_page.click_card_save()
        filtered_chart = self.dashboard_page.get_card(card_title=self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        assert self.dashboard_page.get_paginator_total_num_of_items(filtered_chart) == '24'

        # Remove the filter - expected to generate as many bars as devices
        self.dashboard_page.edit_card(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        self.dashboard_page.remove_chart_segment_filter()
        self.dashboard_page.click_card_save()
        filtered_chart = self.dashboard_page.get_card(card_title=self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        assert self.dashboard_page.get_paginator_total_num_of_items(filtered_chart) == '25'

    def test_dashboard_summary_chart(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_summary_card('Devices', 'Host Name', 'Count', self.TEST_SUMMARY_TITLE_DEVICES)
        self.dashboard_page.wait_for_spinner_to_end()
        # verify card reset config
        self.dashboard_page.verify_card_config_reset_summary_chart(self.TEST_SUMMARY_TITLE_DEVICES)
        summary_chart = self.dashboard_page.get_summary_card_text(self.TEST_SUMMARY_TITLE_DEVICES)
        result_count = int(summary_chart.text)
        summary_chart.click()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == result_count
        assert self.devices_page.find_search_value() == self.SUMMARY_CARD_QUERY_DEVICES
        self.dashboard_page.switch_to_page()
        self.dashboard_page.remove_card(self.TEST_SUMMARY_TITLE_DEVICES)
        self.dashboard_page.add_summary_card('Users', 'Logon Count', 'Count', self.TEST_SUMMARY_TITLE_USERS)
        # verify card reset config
        self.dashboard_page.verify_card_config_reset_summary_chart(self.TEST_SUMMARY_TITLE_USERS)
        summary_chart = self.dashboard_page.get_summary_card_text(self.TEST_SUMMARY_TITLE_USERS)
        result_count = int(summary_chart.text)
        summary_chart.click()
        self.users_page.wait_for_table_to_load()
        assert self.users_page.count_entities() == result_count
        assert self.users_page.find_search_value() == self.SUMMARY_CARD_QUERY_USERS
        self.dashboard_page.switch_to_page()
        self.dashboard_page.remove_card(self.TEST_SUMMARY_TITLE_USERS)
