import time
from math import ceil

import pytest
import requests
from selenium.common.exceptions import NoSuchElementException

from axonius.consts.gui_consts import (DASHBOARD_SPACE_DEFAULT,
                                       DASHBOARD_SPACE_PERSONAL)
from axonius.utils.wait import wait_until
from ui_tests.tests.ui_consts import (READ_WRITE_USERNAME, READ_ONLY_USERNAME, NEW_PASSWORD,
                                      FIRST_NAME, LAST_NAME, JSON_ADAPTER_NAME)
from ui_tests.tests.ui_test_base import TestBase


class TestDashboard(TestBase):
    UNCOVERED_QUERY = 'not (((specific_data.data.adapter_properties == "Agent"' \
                      ' or specific_data.data.adapter_properties == "Manager")))'
    COVERED_QUERY = '((specific_data.data.adapter_properties == "Agent" ' \
                    'or specific_data.data.adapter_properties == "Manager"))'
    SUMMARY_CARD_QUERY_DEVICES = 'specific_data.data.hostname == exists(true)'
    SUMMARY_CARD_QUERY_USERS = 'specific_data.data.logon_count == exists(true) and specific_data.data.logon_count > 0'
    OS_WINDOWS_QUERY = 'specific_data.data.os.type == "Windows"'
    LAST_SEEN_7_DAY_QUERY = 'specific_data.data.last_seen < date("NOW - 7d")'
    INTERSECTION_QUERY = f'({OS_WINDOWS_QUERY}) and ({LAST_SEEN_7_DAY_QUERY})'
    SYMMETRIC_DIFFERENCE_FROM_FIRST_QUERY = f'({OS_WINDOWS_QUERY}) and not ({LAST_SEEN_7_DAY_QUERY})'
    SYMMETRIC_DIFFERENCE_FROM_BASE_QUERY = f'not (({OS_WINDOWS_QUERY}) or ({LAST_SEEN_7_DAY_QUERY}))'
    NO_OS_QUERY = 'not (specific_data.data.os.type == exists(true))'
    SEGMENTATION_PIE_CARD_QUERY = 'specific_data.data.hostname == '
    LONG_TEXT_FOR_CARD_TITLE = 'a very long chart name with more than 30 characters in the chart title'
    TEST_SUMMARY_TITLE_DEVICES = 'test summary devices'
    TEST_SUMMARY_TITLE_USERS = 'test summary users'
    TEST_INTERSECTION_TITLE = 'test intersection'
    TEST_SEGMENTATION_HISTOGRAM_TITLE = 'test segmentation histogram'
    TEST_PAGINATOR_ON_SEGMENTATION_HISTOGRAM = 'test paginator on segmentation histogram - devices'
    TEST_PAGINATOR_ON_SEGMENTATION_USERS = 'test paginator on segmentation - users'
    TEST_PAGINATOR_LINKED_TO_CORRECT_FILTER = 'test paginator linked to correct filter'
    SEGMENTATION_QUERY_USER_AD = 'Segmentation_User_name_AD'
    TEST_SEGMENTATION_PIE_TITLE = 'test segmentation pie'
    TEST_EDIT_CHART_TITLE = 'test edit'

    COVERAGE_SPACE_NAME = 'Coverage Dashboard'
    VULNERABILITY_SPACE_NAME = 'Vulnerability Dashboard'
    CUSTOM_SPACE_PANEL_NAME = 'Segment OS'
    PERSONAL_SPACE_PANEL_NAME = 'Private Segment OS'
    NON_EMPTY_TABLE_ROWS = '.x-table tbody tr[id]'

    TEST_EMPTY_TITLE = 'test empty'

    @pytest.mark.skip('TBD')
    def test_system_empty_state(self):
        self.dashboard_page.switch_to_page()
        assert self.dashboard_page.find_show_me_how_button()
        assert self.dashboard_page.find_see_all_message()
        self.dashboard_page.assert_congratulations_message_found()

    def test_dashboard_empty_title(self):
        """
        Test empty dashboard card with no title, save won't be clickable (disabled) and will "fail" then we actually
        add title and save and it should work
        """
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        with pytest.raises(NoSuchElementException):
            self.dashboard_page.add_comparison_card('Devices', 'Windows Operating System',
                                                    'Devices', 'Linux Operating System', '')

        assert self.dashboard_page.is_chart_save_disabled()
        # this should work after we add the title
        self.dashboard_page.fill_current_chart_title(self.TEST_EDIT_CHART_TITLE)
        assert not self.dashboard_page.is_chart_save_disabled()
        self.dashboard_page.click_card_save()

    def test_dashboard_sanity(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()

        # Allow the caches to be rebuilt
        time.sleep(5)

        # This triggers a dashboard reload
        self.settings_page.switch_to_page()
        self.dashboard_page.switch_to_page()

        mdc_card = self.dashboard_page.find_managed_device_coverage_card()
        assert self.dashboard_page.get_title_from_card(mdc_card) == self.dashboard_page.MANAGED_DEVICE_COVERAGE
        mdc_pie = self.dashboard_page.get_pie_chart_from_card(mdc_card)
        # currently it's 95 covered and 5 uncovered, but it might change in the future
        covered = self.dashboard_page.get_covered_from_pie(mdc_pie)
        assert covered > 80
        uncovered = self.dashboard_page.get_uncovered_from_pie(mdc_pie)
        assert uncovered < 20
        assert covered + uncovered == 100
        sl_card = self.dashboard_page.find_system_lifecycle_card()
        assert self.dashboard_page.get_title_from_card(sl_card) == self.dashboard_page.SYSTEM_LIFECYCLE
        sl_cycle = self.dashboard_page.get_cycle_from_card(sl_card)
        self.dashboard_page.assert_check_in_cycle(sl_cycle)
        self.dashboard_page.assert_cycle_is_stable(sl_cycle)
        self.dashboard_page.assert_cycle_start_and_finish_dates(sl_card)

        nc_card = self.dashboard_page.find_new_chart_card()
        assert self.dashboard_page.get_title_from_card(nc_card) == self.dashboard_page.NEW_CHART
        self.dashboard_page.assert_plus_button_in_card(nc_card)

        dd_card = self.dashboard_page.find_device_discovery_card()
        assert self.dashboard_page.get_title_from_card(dd_card) == self.dashboard_page.DEVICE_DISCOVERY
        self.dashboard_page.find_adapter_in_card(dd_card, 'active_directory_adapter')
        self.dashboard_page.find_adapter_in_card(dd_card, 'json_file_adapter')
        quantities = self.dashboard_page.find_quantity_in_card(dd_card)
        assert quantities[0] + quantities[1] == quantities[2]
        assert quantities[2] >= quantities[3]

        ud_card = self.dashboard_page.find_user_discovery_card()
        assert self.dashboard_page.get_title_from_card(ud_card) == self.dashboard_page.USER_DISCOVERY
        self.dashboard_page.find_adapter_in_card(ud_card, 'active_directory_adapter')
        self.dashboard_page.find_adapter_in_card(ud_card, 'json_file_adapter')
        quantities = self.dashboard_page.find_quantity_in_card(ud_card)
        assert quantities[0] + quantities[1] == quantities[2]
        assert quantities[2] >= quantities[3]

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
        self.dashboard_page.switch_to_page()
        self.dashboard_page.click_covered_pie_slice()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_search_value() == self.COVERED_QUERY

    def test_dashboard_intersection_chart(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_intersection_card('Devices', 'Windows Operating System',
                                                  'Devices Not Seen In Last 7 Days', self.TEST_INTERSECTION_TITLE)
        self.dashboard_page.wait_for_spinner_to_end()
        self.dashboard_page.click_intersection_pie_slice(self.TEST_INTERSECTION_TITLE)
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_search_value() == self.INTERSECTION_QUERY
        self.dashboard_page.switch_to_page()
        self.dashboard_page.wait_for_spinner_to_end()
        self.dashboard_page.click_symmetric_difference_first_query_pie_slice(self.TEST_INTERSECTION_TITLE)
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_search_value() == self.SYMMETRIC_DIFFERENCE_FROM_FIRST_QUERY
        self.dashboard_page.switch_to_page()
        self.dashboard_page.wait_for_spinner_to_end()
        self.dashboard_page.click_symmetric_difference_base_query_pie_slice(self.TEST_INTERSECTION_TITLE)
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.find_search_value() == self.SYMMETRIC_DIFFERENCE_FROM_BASE_QUERY
        self.dashboard_page.switch_to_page()
        self.dashboard_page.wait_for_spinner_to_end()
        self.dashboard_page.remove_card(self.TEST_INTERSECTION_TITLE)

    def test_dashboard_summary_chart(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_summary_card('Devices', 'Host Name', 'Count', self.TEST_SUMMARY_TITLE_DEVICES)
        self.dashboard_page.wait_for_spinner_to_end()
        summary_chart = self.dashboard_page.get_summary_card_text(self.TEST_SUMMARY_TITLE_DEVICES)
        result_count = int(summary_chart.text)
        summary_chart.click()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == result_count
        assert self.devices_page.find_search_value() == self.SUMMARY_CARD_QUERY_DEVICES
        self.dashboard_page.switch_to_page()
        self.dashboard_page.remove_card(self.TEST_SUMMARY_TITLE_DEVICES)

        self.dashboard_page.add_summary_card('Users', 'Logon Count', 'Count', self.TEST_SUMMARY_TITLE_USERS)
        summary_chart = self.dashboard_page.get_summary_card_text(self.TEST_SUMMARY_TITLE_USERS)
        result_count = int(summary_chart.text)
        summary_chart.click()
        self.users_page.wait_for_table_to_load()
        assert self.users_page.count_entities() == result_count
        assert self.users_page.find_search_value() == self.SUMMARY_CARD_QUERY_USERS
        self.dashboard_page.switch_to_page()
        self.dashboard_page.remove_card(self.TEST_SUMMARY_TITLE_USERS)

    def test_new_chart_stress(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        for i in range(10):
            self.dashboard_page.add_summary_card('Devices', 'Host Name', 'Count',
                                                 f'{self.TEST_SUMMARY_TITLE_DEVICES}{i}')
            self.dashboard_page.wait_for_spinner_to_end()
            self.dashboard_page.get_card(f'{self.TEST_SUMMARY_TITLE_DEVICES}{i}')
        last_card = self.dashboard_page.get_all_cards()[-1]
        assert self.dashboard_page.get_title_from_card(last_card) == 'New Chart'
        for j in range(10):
            self.dashboard_page.remove_card(f'{self.TEST_SUMMARY_TITLE_DEVICES}{j}')
            self.dashboard_page.wait_for_spinner_to_end()

    def _create_get_paginator_segmentation_card(self, run_discovery, module, field, title, view_name):
        self.dashboard_page.switch_to_page()
        if run_discovery:
            self.base_page.run_discovery()
        self.dashboard_page.add_segmentation_card(module=module,
                                                  field=field,
                                                  title=title,
                                                  view_name=view_name,
                                                  partial_text=False)
        # create reference to the segmentation card with title
        segmentation_card = self.dashboard_page.get_card(title)
        # create reference to the histogram within the card
        return self.dashboard_page.get_histogram_chart_from_card(segmentation_card)

    def _test_paginator_state_first_page(self, histograms_chart, page_number, to_val):
        assert not self.dashboard_page.is_missing_paginator_num_of_items(histograms_chart)
        assert self.dashboard_page.is_missing_paginator_from_item(histograms_chart)
        assert self.dashboard_page.is_missing_paginator_to_item(histograms_chart)
        assert int(self.dashboard_page.get_paginator_to_item_number(histograms_chart, page_number)) == to_val
        assert self.dashboard_page.check_paginator_buttons_state(histograms_chart, True, True, False, False)

    def _test_paginator_state_middle_page(self, histograms_chart, page_number, to_val, from_val):
        assert self.dashboard_page.is_missing_paginator_num_of_items(histograms_chart)
        assert not self.dashboard_page.is_missing_paginator_from_item(histograms_chart)
        assert not self.dashboard_page.is_missing_paginator_to_item(histograms_chart)
        assert self.dashboard_page.check_paginator_buttons_state(histograms_chart, False, False, False, False)
        assert int(self.dashboard_page.get_paginator_to_item_number(histograms_chart, page_number)) == to_val
        assert int(self.dashboard_page.get_paginator_from_item_number(histograms_chart)) == from_val

    def _test_paginator_state_last_page(self, histograms_chart, page_number, to_val, from_val):
        assert self.dashboard_page.is_missing_paginator_num_of_items(histograms_chart)
        assert not self.dashboard_page.is_missing_paginator_from_item(histograms_chart)
        assert not self.dashboard_page.is_missing_paginator_to_item(histograms_chart)
        assert not self.dashboard_page.is_missing_paginator_from_item(histograms_chart)
        assert not self.dashboard_page.is_missing_paginator_to_item(histograms_chart)
        assert int(self.dashboard_page.get_paginator_to_item_number(histograms_chart, page_number)) == to_val
        assert int(self.dashboard_page.get_paginator_from_item_number(histograms_chart)) == from_val
        assert self.dashboard_page.check_paginator_buttons_state(histograms_chart, False, False, True, True)

    @staticmethod
    def _check_num_of_histograms_items_fit_paginator_number(page_number, num_of_pages, num_of_histogram_lines,
                                                            num_of_items, total_num_of_items, limit):
        # num_of_items: it represents the number of items that we reached on the current page...
        #               it is the so called "TO" number in the pagination"
        # if number of histogram items fit the "To" value of the Paginator
        if page_number != num_of_pages:
            # in case we are not in the last page we expect the num_of_histogram_lines to fit
            # the num_of_items divided by the current page number
            assert num_of_histogram_lines == num_of_items / page_number
        else:
            # in case we are in last page we expect the num_of_histogram_lines to be:
            # the reminder of total_num_of_items % limit
            # if total_num_of_items != limit == 0
            # otherwise should as in previous case
            if total_num_of_items % limit == 0:
                assert num_of_histogram_lines == num_of_items / page_number
            else:
                assert num_of_histogram_lines == total_num_of_items % limit

    def _gather_paginator_iteration_data(self, histograms_chart, page_number, num_of_pages, total_num_of_items,
                                         limit):
        num_of_histogram_lines = self.dashboard_page.get_count_histogram_lines_from_histogram(histograms_chart)
        num_of_items = int(self.dashboard_page.get_paginator_to_item_number(histograms_chart, page_number))
        # calculate Paginator 'To' value
        to_val = self.dashboard_page.calculate_to_item_value(num_of_items, page_number, limit)
        # calculate Paginator 'From' value
        from_val = self.dashboard_page.calculate_from_item_value(num_of_items, num_of_pages,
                                                                 page_number, to_val, limit)
        return num_of_histogram_lines, num_of_items, to_val, from_val

    def grab_all_host_names_from_devices(self):
        self.devices_page.switch_to_page()
        self.devices_page.select_page_size(50)
        return self.devices_page.get_column_data(self.devices_page.FIELD_HOSTNAME_TITLE)

    @staticmethod
    def assert_data_devices_fit_pagination_data(histogram_items_title, host_names_list):
        # Checking the lists are equal by one sided containment + equal length
        assert len(histogram_items_title) == len(host_names_list)
        assert all(item in host_names_list for item in histogram_items_title)

    def generate_csv_from_segmentation_graph(self, panel_id):
        session = requests.Session()
        cookies = self.driver.get_cookies()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])
        return session.get(f'https://127.0.0.1/api/dashboards/panels/{panel_id}/csv')

    def grab_all_host_names_from_csv(self, panel_id):
        result = self.generate_csv_from_segmentation_graph(panel_id)
        all_csv_rows = result.content.decode('utf-8').split('\r\n')
        csv_headers = all_csv_rows[0].split(',')
        csv_data_rows = all_csv_rows[1:-1]
        return [str.split(',')[0] for str in csv_data_rows]

    def get_segmentation_card_id(self):
        segmentation_card = self.dashboard_page.get_card(self.TEST_PAGINATOR_ON_SEGMENTATION_HISTOGRAM)
        card_id = segmentation_card.get_property('id')
        return card_id

    def test_check_segmentation_csv(self):
        histogram_items_title = []
        histograms_chart = \
            self._create_get_paginator_segmentation_card(run_discovery=True,
                                                         module='Devices',
                                                         field='Host Name',
                                                         title=self.TEST_PAGINATOR_ON_SEGMENTATION_HISTOGRAM,
                                                         view_name='')
        panel_id = self.get_segmentation_card_id()
        limit = int(self.dashboard_page.get_paginator_num_of_items(histograms_chart))
        total_num_of_items = int(self.dashboard_page.get_paginator_total_num_of_items(histograms_chart))
        # calculate the total number of pages in Paginator
        # by this wat we ensure to have the exact num of pages and cover all the cases even if the
        # total_num_of_items % limit has a remainder (round up the result)
        num_of_pages = ceil(total_num_of_items / limit)
        # iterate incrementaly on all the pages (next)
        for page_number in range(1, num_of_pages + 1):
            histogram_items_title.append(self.dashboard_page.get_histogram_items_title_on_pagination(histograms_chart))
            if page_number == 1:
                self.dashboard_page.click_to_next_page(histograms_chart)
            elif page_number == num_of_pages:
                break
            else:
                self.dashboard_page.click_to_next_page(histograms_chart)
        # flatten list
        histogram_titles_list = [item for sublist in histogram_items_title for item in sublist]
        host_names_list = self.grab_all_host_names_from_csv(panel_id)
        # compare histograms_item_titles of pagination with data grabbed from devices table
        self.assert_data_devices_fit_pagination_data(histogram_titles_list, host_names_list)
        self.dashboard_page.remove_card(self.TEST_PAGINATOR_ON_SEGMENTATION_HISTOGRAM)

    def test_paginator_paginator_update_after_discovery(self):
        self.users_page.switch_to_page()
        self.base_page.run_discovery()
        wait_until(lambda: self.devices_queries_page.get_table_count() > 0)
        self.devices_page.click_query_wizard()
        expressions = self.devices_page.find_expressions()
        assert len(expressions) == 1
        self.users_page.select_query_adapter(JSON_ADAPTER_NAME)
        self.devices_page.toggle_not(expressions[0])
        self.users_page.click_search()
        self.users_page.wait_for_table_to_load()
        self.users_page.click_save_query()
        self.users_page.fill_query_name(self.SEGMENTATION_QUERY_USER_AD)
        self.users_page.click_save_query_save_button()
        first_result_count = self.users_page.count_entities()
        self.users_page.click_row_checkbox(1)
        self.users_page.click_row_checkbox(2)
        self.users_page.click_row_checkbox(3)
        self.users_page.open_delete_dialog()
        self.users_page.confirm_delete()
        self.users_page.wait_for_table_to_load()
        second_result_count = self.users_page.count_entities()
        assert second_result_count == first_result_count - 3
        histograms_chart = \
            self._create_get_paginator_segmentation_card(run_discovery=False,
                                                         module='Users',
                                                         field='User Name',
                                                         title=self.TEST_PAGINATOR_ON_SEGMENTATION_USERS,
                                                         view_name=self.SEGMENTATION_QUERY_USER_AD)
        total_num_of_items = int(self.dashboard_page.get_paginator_total_num_of_items(histograms_chart))
        assert total_num_of_items == second_result_count
        self.base_page.run_discovery()
        wait_until(lambda: int(
            self.dashboard_page.get_paginator_total_num_of_items(histograms_chart)) == first_result_count)
        self.dashboard_page.remove_card(self.TEST_PAGINATOR_ON_SEGMENTATION_USERS)

    def test_multi_page_histogram_linked_to_correct_filter(self):
        histograms_chart = \
            self._create_get_paginator_segmentation_card(run_discovery=True,
                                                         module='Devices',
                                                         field='Host Name',
                                                         title=self.TEST_PAGINATOR_LINKED_TO_CORRECT_FILTER,
                                                         view_name='')
        # on First Page
        selected_item_bart_title = self.dashboard_page.get_histogram_bar_item_title(histograms_chart, 1)
        self.dashboard_page.click_on_histogram_item(histograms_chart, 1)
        # assert that the query is correct
        assert self.devices_page.find_query_search_input().get_attribute('value') == \
            f'specific_data.data.hostname == "{selected_item_bart_title}"'
        self.dashboard_page.switch_to_page()
        # create reference to the histogram within the card
        segmentation_card = self.dashboard_page.get_card(self.TEST_PAGINATOR_LINKED_TO_CORRECT_FILTER)
        # set focus back on the histogram chart (after switching page)
        histograms_chart = self.dashboard_page.get_histogram_chart_from_card(segmentation_card)
        # Got to Last Page
        self.dashboard_page.click_to_last_page(histograms_chart)
        selected_item_bart_title = self.dashboard_page.get_histogram_bar_item_title(histograms_chart, 1)
        self.dashboard_page.click_on_histogram_item(histograms_chart, 1)
        # assert that the query is correct
        assert self.devices_page.find_query_search_input().get_attribute('value') == \
            f'specific_data.data.hostname == "{selected_item_bart_title}"'
        self.dashboard_page.switch_to_page()
        self.dashboard_page.remove_card(self.TEST_PAGINATOR_LINKED_TO_CORRECT_FILTER)

    def test_paginator_on_segmentation_chart(self):
        histogram_items_title = []
        first_page = 1
        histograms_chart = self._create_get_paginator_segmentation_card(
            run_discovery=True,
            module='Devices',
            field='Host Name',
            title=self.TEST_PAGINATOR_ON_SEGMENTATION_HISTOGRAM,
            view_name='')
        assert not self.dashboard_page.is_missing_paginator_navigation(histograms_chart)
        limit = int(self.dashboard_page.get_paginator_num_of_items(histograms_chart))
        total_num_of_items = int(self.dashboard_page.get_paginator_total_num_of_items(histograms_chart))
        # calculate the total number of pages in Paginator
        # by this wat we ensure to have the exact num of pages and cover all the cases even if the
        # total_num_of_items % limit has a remainder ((round up the result)
        num_of_pages = ceil(total_num_of_items / limit)
        # iterate incrementaly on all the pages (next)
        for page_number in range(1, num_of_pages + 1):
            num_of_histogram_lines, num_of_items, to_val, from_val = \
                self._gather_paginator_iteration_data(histograms_chart, page_number, num_of_pages,
                                                      total_num_of_items, limit)
            self._check_num_of_histograms_items_fit_paginator_number(page_number, num_of_pages,
                                                                     num_of_histogram_lines,
                                                                     num_of_items,
                                                                     total_num_of_items,
                                                                     limit)
            if page_number == 1:
                self._test_paginator_state_first_page(histograms_chart, page_number, to_val)
                self.dashboard_page.click_to_next_page(histograms_chart)
            elif page_number == num_of_pages:
                self._test_paginator_state_last_page(histograms_chart, page_number, to_val,
                                                     from_val)
            else:
                self._test_paginator_state_middle_page(histograms_chart, page_number, to_val,
                                                       from_val)
                self.dashboard_page.click_to_next_page(histograms_chart)
        # iterate decrementaly on all the  pages (back)
        for page_number in range(num_of_pages, 0, -1):
            num_of_histogram_lines, num_of_items, to_val, from_val = \
                self._gather_paginator_iteration_data(histograms_chart, page_number, num_of_pages,
                                                      total_num_of_items, limit)
            self._check_num_of_histograms_items_fit_paginator_number(page_number, num_of_pages,
                                                                     num_of_histogram_lines,
                                                                     num_of_items,
                                                                     total_num_of_items,
                                                                     limit)
            histogram_items_title.append(self.dashboard_page.get_histogram_items_title_on_pagination(histograms_chart))
            if page_number == 1:
                self._test_paginator_state_first_page(histograms_chart, page_number, to_val)
            elif page_number == num_of_pages:
                self._test_paginator_state_last_page(histograms_chart, page_number, to_val, from_val)
                self.dashboard_page.click_to_previous_page(histograms_chart)
            else:
                self._test_paginator_state_middle_page(histograms_chart, page_number, to_val, from_val)
                self.dashboard_page.click_to_previous_page(histograms_chart)
        # flatten list
        histogram_titles_list = [item for sublist in histogram_items_title for item in sublist]
        devices_tiles_list = self.grab_all_host_names_from_devices()
        self.assert_data_devices_fit_pagination_data(histogram_titles_list, devices_tiles_list)
        self.dashboard_page.switch_to_page()
        # create reference to the histogram within the card
        segmentation_card = self.dashboard_page.get_card(self.TEST_PAGINATOR_ON_SEGMENTATION_HISTOGRAM)
        # set focus back on the histogram chart (after switching page)
        histograms_chart = self.dashboard_page.get_histogram_chart_from_card(segmentation_card)
        # Got to Last Page
        page_number = num_of_pages
        self.dashboard_page.click_to_last_page(histograms_chart)
        num_of_items = int(self.dashboard_page.get_paginator_to_item_number(histograms_chart, page_number))
        # calculate Paginator 'To' value
        to_val = self.dashboard_page.calculate_to_item_value(num_of_items, page_number, limit)
        # calculate Paginator 'From' value
        from_val = self.dashboard_page.calculate_from_item_value(num_of_items, num_of_pages,
                                                                 page_number, to_val, limit)
        self._test_paginator_state_last_page(histograms_chart, page_number, to_val, from_val)
        # Go to First Page
        page_number = 1
        self.dashboard_page.click_to_first_page(histograms_chart)
        num_of_items = int(self.dashboard_page.get_paginator_to_item_number(histograms_chart, page_number))
        # calculate Paginator 'To' value
        to_val = self.dashboard_page.calculate_to_item_value(num_of_items, page_number, limit)
        self._test_paginator_state_first_page(histograms_chart, page_number, to_val)
        self.dashboard_page.remove_card(self.TEST_PAGINATOR_ON_SEGMENTATION_HISTOGRAM)

    def test_dashboard_segmentation_chart(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_segmentation_card('Devices', 'OS: Type', self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        shc_card = self.dashboard_page.get_card(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        shc_chart = self.dashboard_page.get_histogram_chart_from_card(shc_card)
        line = self.dashboard_page.get_histogram_line_from_histogram(shc_chart, 1)
        first_result_count = int(line.text)
        line.click()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() == first_result_count
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
        self.dashboard_page.remove_card(self.TEST_SEGMENTATION_HISTOGRAM_TITLE)
        self.dashboard_page.remove_card(self.TEST_SEGMENTATION_PIE_TITLE)

    def _does_user_appear(self):
        results = self.dashboard_page.get_all_table_rows()
        return len(results) > 1 and results[1]

    def test_dashboard_search(self):
        string_to_search = 'be'
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.fill_query_value(string_to_search)
        self.dashboard_page.enter_search()
        self.dashboard_page.wait_for_table_to_load()
        wait_until(self._does_user_appear)
        results = self.dashboard_page.get_all_table_rows()
        host_name = results[0][0]
        user_name = results[1][0]
        tables_count = self.dashboard_page.get_all_tables_counters()
        dashboard_devices_table_count = tables_count[0]
        dashboard_users_table_count = tables_count[1]
        assert len(results) == dashboard_devices_table_count + dashboard_users_table_count
        for result in results:
            assert any(string_to_search in s.lower() for s in result)
        self.dashboard_page.open_view_devices()
        self.devices_page.wait_for_table_to_load()
        devices_page_tables_count = self.devices_page.get_all_tables_counters()[0]
        assert devices_page_tables_count == dashboard_devices_table_count
        assert self.devices_page.find_search_value() == string_to_search
        assert any(host_name in s for s in self.devices_page.get_all_table_rows()[0])
        self.devices_page.page_back()
        self.dashboard_page.open_view_users()
        self.users_page.wait_for_table_to_load()
        users_tables_count = self.users_page.get_all_tables_counters()[0]
        assert users_tables_count == dashboard_users_table_count
        assert self.users_page.find_search_value() == string_to_search
        assert any(user_name in s for s in self.users_page.get_all_table_rows()[0])
        self.users_page.page_back()
        device_id = self.devices_page.find_first_id()
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.click_row()
        self.devices_page.wait_for_spinner_to_end()
        assert device_id in self.driver.current_url
        hostname = self.devices_page.get_value_for_label_in_device_page(self.devices_page.FIELD_HOSTNAME_TITLE)
        assert hostname == 'EC2AMAZ-61GTBER.TestDomain.test'

    def test_dashboard_search_url(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.driver.get(f'{self.driver.current_url}dashboard/explorer?search=dc')
        self.dashboard_page.wait_for_table_to_load()
        wait_until(self._does_user_appear)
        assert self.dashboard_page.get_all_tables_counters() == [4, 0]

    def test_dashboard_single_demo_view(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.switch_to_page()

        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_load()
        self.devices_queries_page.wait_for_spinner_to_end()
        assert len(self.devices_queries_page.find_query_name_by_part('DEMO')) == 1

        self.dashboard_page.switch_to_page()
        self.driver.refresh()
        self.devices_queries_page.switch_to_page()
        self.devices_queries_page.wait_for_table_to_load()
        self.devices_queries_page.wait_for_spinner_to_end()
        assert len(self.devices_queries_page.find_query_name_by_part('DEMO')) == 1

    def test_dashboard_spaces(self):
        # Default space and Personal space existing
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.switch_to_page()
        assert self.dashboard_page.find_active_space_header_title() == DASHBOARD_SPACE_DEFAULT
        assert self.dashboard_page.find_space_header_title(2) == DASHBOARD_SPACE_PERSONAL

        # Add new space and name it
        self.dashboard_page.add_new_space(self.COVERAGE_SPACE_NAME)
        wait_until(lambda: self.dashboard_page.find_space_header_title(3) == self.COVERAGE_SPACE_NAME)

        # Rename an existing space
        self.dashboard_page.rename_space(self.VULNERABILITY_SPACE_NAME, 3)
        wait_until(lambda: self.dashboard_page.find_space_header_title(3) == self.VULNERABILITY_SPACE_NAME)
        assert self.dashboard_page.is_missing_space(self.COVERAGE_SPACE_NAME)
        self.dashboard_page.add_new_space(self.COVERAGE_SPACE_NAME)

        # Add a panel to a custom space
        self.dashboard_page.find_space_header(3).click()
        self.dashboard_page.add_segmentation_card('Devices', 'OS: Type', self.CUSTOM_SPACE_PANEL_NAME)
        self.dashboard_page.wait_for_spinner_to_end()
        segment_card = self.dashboard_page.get_card(self.CUSTOM_SPACE_PANEL_NAME)
        assert segment_card and self.dashboard_page.get_histogram_chart_from_card(segment_card)
        self.dashboard_page.find_space_header(1).click()
        assert self.dashboard_page.is_missing_panel(self.CUSTOM_SPACE_PANEL_NAME)
        self.dashboard_page.find_space_header(2).click()
        assert self.dashboard_page.is_missing_panel(self.CUSTOM_SPACE_PANEL_NAME)

        # Add a panel to the Personal space and check hidden from other user
        self.dashboard_page.add_segmentation_card('Devices', 'OS: Type', self.PERSONAL_SPACE_PANEL_NAME)
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(READ_WRITE_USERNAME, NEW_PASSWORD,
                                           FIRST_NAME, LAST_NAME,
                                           role_name=self.settings_page.ADMIN_ROLE)
        self.settings_page.create_new_user(READ_ONLY_USERNAME, NEW_PASSWORD,
                                           FIRST_NAME, LAST_NAME,
                                           role_name=self.settings_page.READ_ONLY_ROLE)
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=READ_WRITE_USERNAME, password=NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.find_space_header(2).click()
        assert self.dashboard_page.is_missing_panel(self.PERSONAL_SPACE_PANEL_NAME)
        assert not self.dashboard_page.is_missing_space(self.VULNERABILITY_SPACE_NAME)
        self.dashboard_page.find_space_header(3).click()
        assert not self.dashboard_page.is_missing_panel(self.CUSTOM_SPACE_PANEL_NAME)
        self.dashboard_page.remove_card(self.CUSTOM_SPACE_PANEL_NAME)
        assert not self.dashboard_page.is_missing_space(self.COVERAGE_SPACE_NAME)
        self.dashboard_page.remove_space(3)
        self.dashboard_page.rename_space(self.VULNERABILITY_SPACE_NAME, 3)

        # Remove a space
        assert self.dashboard_page.is_missing_space(self.COVERAGE_SPACE_NAME)
        self.dashboard_page.remove_space(3)
        assert self.dashboard_page.is_missing_space(self.VULNERABILITY_SPACE_NAME)

        # Login with Read Only user and see it cannot add a space
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=READ_ONLY_USERNAME, password=NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        assert self.dashboard_page.is_missing_space(DASHBOARD_SPACE_PERSONAL)
        assert self.dashboard_page.is_missing_add_space()

    def test_dashboard_edit(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_comparison_card('Devices', 'Windows Operating System',
                                                'Devices', 'Linux Operating System',
                                                self.TEST_EDIT_CHART_TITLE)
        self.dashboard_page.edit_card(self.TEST_EDIT_CHART_TITLE)
        self.dashboard_page.add_comparison_card_view('Devices', 'IOS Operating System')

    def test_dashboard_empty_segmentation_chart(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_segmentation_card(module='Devices',
                                                  field='OS: Type',
                                                  title=self.TEST_EMPTY_TITLE,
                                                  view_name='OS X Operating System')

        assert self.dashboard_page.find_no_data_label()
        self.dashboard_page.remove_card(self.TEST_EMPTY_TITLE)

    def test_dashboard_empty_intersection_chart(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_intersection_card(module='Devices',
                                                  view_name='OS X Operating System',
                                                  first_query='OS X Operating System',
                                                  second_query='OS X Operating System',
                                                  title=self.TEST_EMPTY_TITLE)

        assert self.dashboard_page.find_no_data_label()
        self.dashboard_page.remove_card(self.TEST_EMPTY_TITLE)

    def test_dashboard_empty_comparison_chart(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.dashboard_page.add_comparison_card(first_module='Devices',
                                                first_query='OS X Operating System',
                                                second_module='Devices',
                                                second_query='OS X Operating System',
                                                title=self.TEST_EMPTY_TITLE,
                                                chart_type='pie')

        assert self.dashboard_page.find_no_data_label()
        self.dashboard_page.remove_card(self.TEST_EMPTY_TITLE)
