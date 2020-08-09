import datetime
import re
import time
from contextlib import contextmanager
from decimal import Decimal, getcontext
import pytest
from retrying import retry
from selenium.common.exceptions import (ElementClickInterceptedException,
                                        NoSuchElementException)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.color import Color

from axonius.utils.wait import wait_until
from services.axon_service import TimeoutException
from ui_tests.pages.base_page import BasePage

# pylint: disable=too-many-lines


class DashboardPage(BasePage):
    SHOW_ME_HOW = 'SHOW ME HOW'
    CONGRATULATIONS = 'Congratulations! You are one step closer to'
    MANAGED_DEVICE_COVERAGE = 'Managed Device Coverage'
    VA_SCANNER_COVERAGE = 'VA Scanner Coverage'
    ENDPOINT_PROTECTION_COVERAGE = 'Endpoint Protection Coverage'
    SYSTEM_LIFECYCLE = 'System Lifecycle'
    NEW_CHART = 'New Chart'
    DEVICE_DISCOVERY = 'Device Discovery'
    USER_DISCOVERY = 'User Discovery'
    QUERY_SEARCH_INPUT_CSS = 'div:nth-child(1) > div > div > input'
    SEARCH_INSIGHTS_CSS = '.x-search-insights'
    CHART_WIZARD_DATEPICKER_CSS = '.x-chart-wizard .x-date-edit.labeled:nth-of-type({child_index}) input'
    CHART_WIZARD_TYPE_SWITCH_CSS = '.x-chart-wizard .md-switch-container + label'
    PIE_SLICE_CSS = 'g[class^="slice-"]'
    PIE_SLICE_TEXT_BY_POSITION = 'svg > g.slice-{index} > text'
    UNCOVERED_PIE_SLICE_CSS = 'svg > g.slice-0 > text.scaling'
    COVERED_PIE_SLICE_CSS = 'svg > g.slice-1 > text.scaling'
    INTERSECTION_PIE_INTERSECTION_SLICE_CSS = 'svg > g.slice-2 > text'
    SYMMETRIC_DIFFERENCE_FROM_BASE_QUERY_SLICE_CSS = 'svg > g.slice-0 > text'
    SYMMETRIC_DIFFERENCE_FROM_FIRST_QUERY_SLICE_CSS = 'svg > g.slice-1 > text'
    NEW_CARD_WIZARD_CSS = '.x-tab.active .x-card.chart-new .x-button'
    NEW_CARD_WIZARD_OVERLAY_CSS = '.x-modal .x-chart-wizard'
    CHART_METRIC_DROP_DOWN_CSS = '#metric > div'
    INTERSECTION_CHART_FIRST_QUERY_DROP_DOWN_CSS = '#intersectingFirst > div'
    INTERSECTION_CHART_SECOND_QUERY_DROP_DOWN_CSS = '#intersectingSecond > div'
    WIZARD_OPTIONS_CSS = 'div.x-select-options > div.x-select-option'
    CHART_WIZARD_CSS = '.x-chart-wizard'
    CHART_MODULE_DROP_DOWN_CSS = '.x-chart-wizard .x-select.x-select-symbol'
    SELECT_VIEWS_CSS = '.x-select-views'
    SELECT_VIEWS_ADD_BUTTON = 'add_view'
    SELECT_VIEWS_VIEW_CSS = '.view'
    SELECT_VIEW_NAME_CSS = '.view-name'
    CHART_TIMELINE_LAST_RANGE_RADIO_CSS = '#range_relative'
    CHART_TIMELINE_DATE_RANGE_RADIO_CSS = '#range_absolute'
    CHART_FIELD_DROP_DOWN_CSS = '.x-dropdown.x-select.field-select'
    CHART_DROPDOWN_FIELD_VALUE_CSS = '.x-select .x-select-trigger .trigger-text'
    CHART_ADAPTER_DROP_DOWN_CSS = '.x-dropdown.x-select.x-select-symbol.minimal'
    CHART_FIELD_TEXT_BOX_CSS = 'div.x-search-input.x-select-search > input'
    CHART_FUNCTION_CSS = 'div.x-chart-metric.grid-span2 > div:nth-child(8)'
    CHART_TITLE_ID = 'chart_name'
    MATRIX_WIZARD_BASE_QUERY_CSS = '.base-query-row:nth-child({index}) .x-dropdown.x-select'
    MATRIX_WIZARD_ADD_BASE_QUERY_CSS = '#add-base-query'
    MATRIX_WIZARD_INTERSECTING_QUERY_CSS = '.intersection-query-row:nth-child({index}) .x-dropdown.x-select'
    MATRIX_WIZARD_ADD_INTERSECTING_QUERY_CSS = '#add-intersecting-query'
    MATRIX_GROUP_CSS = '.intersection-group:nth-child(odd)'
    MATRIX_GROUP_NAME_CSS = '.group-name'
    MATRIX_GROUP_TOTAL_CSS = '.group-total'
    MATRIX_GROUP_SLICES = '.intersection-slice'
    MATRIX_TOTAL_COUNT_CSS = '.stacked-total'
    SEGMENTATION_FILTER_INPUT_CSS = '.x-filter-contains .x-filter-expression-contains:nth-child({index}) input'
    SEGMENTATION_FILTER_DELETE_CSS = '.x-filter-contains .x-filter-expression-contains:nth-child({index}) button'
    SEGMENTATION_FILTER_DROP_DOWN_CSS = '.x-filter-contains .x-filter-expression-contains:nth-child({index})' \
                                        ' .x-dropdown'
    SEGMENTATION_ADD_FILTER_BUTTON_CSS = '.x-filter-contains > button'
    SUMMARY_CARD_TEXT_CSS = 'div.x-summary > div.summary'
    CARD_MENU_BTN_CSS = '.card_menu'
    CARD_CLOSE_BTN_ID = 'remove_chart'
    CARD_CLOSE_BTN_TEXT = 'Delete Chart'
    CARD_EDIT_BTN_ID = 'edit_chart'
    CARD_EDIT_BTN_TEXT = 'Edit Chart'
    SPACE_DELETE_BTN_TEXT = 'Delete Space'
    CARD_EXPORT_TO_CSV_BTN_CSS = '.actions > .export'
    CARD_SEARCH_INPUT_CSS = '.x-search-input > input'
    BANNER_BY_TEXT_XPATH = '//div[contains(@class, \'x-banner\') and .//text() = \'{banner_text}\']'
    BANNER_BY_CSS = '.x-banner'
    BANNER_NO_CONTRACT_CLASS = '.x-contract-banner'
    SPACES_XPATH = '//div[@class=\'x-spaces\']'
    ACTIVE_SPACE_HEADERS_XPATH = f'{SPACES_XPATH}//li[@class=\'header-tab active\']'
    SPACE_HEADERS_XPATH = f'{SPACES_XPATH}//li[contains(@class, \'header-tab\')]'
    SPACE_HEADER_CSS = '.x-spaces .x-tabs .header-tab:nth-child({tab_index})'
    NEW_SPACE_BUTTON_XPATH = f'{SPACES_XPATH}//li[@class=\'add-tab\']'
    RENAME_SPACE_INPUT_ID = 'rename_space'
    EDIT_SPACE_MENU_ITEM_ID = 'edit_space'
    REMOVE_SPACE_MENU_ITEM_ID = 'remove_space'
    SPACE_ACCESS_RADIO_BUTTON_ID = 'roles_space_access'
    SPACE_ROLES_SELECT_ID = '#select_space'
    SPACE_ROLES_DROPDOWN_CSS = '.x-multiple-select-dropdown'
    SPACE_ACTION_MENU_CSS = '.x-spaces .x-tabs .header .action-trigger'
    PANEL_BY_NAME_XPATH = '//div[contains(@class, \'x-tab active\')]//div[contains(@class, \'x-card\') ' \
                          'and .//text()=\'{panel_name}\']'
    NO_DATA_FOUND_TEXT = 'No data found'
    PAGINATOR_CLASS = '.x-paginator'
    PAGINATOR_LIMIT = '.num-of-items'
    PAGINATOR_TO = ' .to-item'
    PAGINATOR_BUTTON = f'{PAGINATOR_CLASS} .x-button'
    PAGINATOR_FIRST_PAGE_BUTTON = f'{PAGINATOR_BUTTON}.ant-btn-link.first'
    PAGINATOR_PREVIOUS_PAGE_BUTTON = f'{PAGINATOR_BUTTON}.ant-btn-link.previous'
    PAGINATOR_NEXT_PAGE_BUTTON = f'{PAGINATOR_BUTTON}.ant-btn-link.next'
    PAGINATOR_LAST_PAGE_BUTTON = f'{PAGINATOR_BUTTON}.ant-btn-link.last'
    HISTOGRAM_ITEMS = '.histogram-container .histogram-item'
    PAGINATOR_NUM_OF_ITEMS = f'{PAGINATOR_CLASS} {PAGINATOR_LIMIT}'
    PAGINATOR_TOTAL_NUM_OF_ITEMS = f'{PAGINATOR_CLASS} .total-num-of-items'
    PAGINATOR_FROM_VALUE = f'{PAGINATOR_CLASS} .from-item'
    PAGINATOR_TO_VALUE = f'{PAGINATOR_CLASS} {PAGINATOR_TO}'
    CHART_QUERY_DEFAULT = 'QUERY...'
    CHART_QUERY_ALL_DEFAULT = 'QUERY (OR EMPTY FOR ALL)'
    CARD_FILTER_CSS = '.x-select .x-select-trigger .placeholder'
    CARD_FIELD_CSS = '.x-select-typed-field .x-select-trigger .placeholder'
    COMPARISON_CARD_1ST_CHILD_MODLUE_CSS = 'div:nth-child(1) > div.x-dropdown.x-select.x-select-symbol'
    COMPARISON_CARD_2ND_CHILD_MODULE_CSS = 'div:nth-child(2) > div.x-dropdown.x-select.x-select-symbol'
    COMPARISON_CARD_1ST_QUERY_CSS = 'div:nth-child(1) > div.x-dropdown.x-select.view-name'
    COMPARISON_CARD_2ND_QUERY_CSS = 'div:nth-child(2) > div.x-dropdown.x-select.view-name'
    CARD_SPINNER_CSS = '.chart-spinner'
    NO_DATA_FOUND_SPINNER_CSS = '.no-data-found'
    LIFECYCLE_TOOLTIP_CSS = '.cycle-wrapper .x-tooltip'
    LIFECYCLE_TABLE_CSS = '.cycle-wrapper .table'
    WIZARD_SORT_BY = '#sort_by_{sort_by}'
    WIZARD_SORT_ORDER = '#sort_order_{sort_order}'
    WIZARD_SORT_CONTAINER_CSS = '.sort-container'
    CHART_PANEL_SORT_ACTION_ID = 'sort_chart'
    CHART_PANEL_SORT_BY_ID = 'chart_sort_by_{sort_by}'
    CHART_PANEL_SORT_ORDER_ID = 'chart_sort_order_{sort_by}_{sort_order}'

    TOGGLE_LEGEND_CSS = '.toggle-legend'
    CHART_LEGEND_CSS = '.x-chart-legend'

    COLOR_DANGEROUS = '#FA6400'
    COLOR_VERYDANGEROUS = '#D0021C'
    COLOR_INFO = '#3498DB'

    NEW_CARD_CHART_CSS = '.x-tab.active .x-card.chart-new'
    EXPLORER_RESULTS_CSS = '.explorer-results'
    TRIAL_BANNER_CSS = '.x-trial-banner'

    TOOLTIP_HEADER_CONTENT_CSS = '.x-tooltip .header-content'
    TOOLTIP_BODY_CONTENT_CSS = '.x-tooltip .body-content'
    MOVE_OR_COPY_MODAL_ID = 'move_or_copy'
    MOVE_OR_COPY_SPACE_SELECT_ID = 'select_space'
    MOVE_OR_COPY_SPACE_DROPDOWN_CSS = '.ant-select-dropdown'
    MOVE_OR_COPY_SPACE_DROPDOWN_ITEM_CSS = '.ant-select-dropdown-menu-item'

    PIE_CHART_TYPE = 'pie'
    HISTOGRAM_CHART_TYPE = 'histogram'
    SUMMARY_CHART_TYPE = 'summary'
    TIMELINE_CHART_TYPE = 'timeline'

    TEST_TIMELINE_SVG_CSS = 'svg[aria-label="A chart."] g:nth-child(4) g:nth-child(2) g:nth-child(2) path'
    CHART_WARNING_CSS = '.chart-warning'
    TIMELINE_CARD_DATA_TABLE_CSS = '.x-line svg + div table tbody'

    PIE_TOTAL_ITEMS_CSS = '.pie-total'

    @property
    def root_page_css(self):
        return 'li#dashboard.x-nav-item'

    @property
    def url(self):
        return f'{self.base_url}'

    def find_show_me_how_button(self):
        return self.get_button(self.SHOW_ME_HOW)

    def find_see_all_message(self):
        return self.find_element_by_text('SEE ALL TO SECURE ALL')

    def assert_congratulations_message_found(self):
        assert f'{self.CONGRATULATIONS}\nhaving all your assets visible in one place.' in self.find_element_by_text(
            self.CONGRATULATIONS).text

    def find_managed_device_coverage_card(self):
        return self.driver.find_element_by_xpath(
            self.PANEL_BY_NAME_XPATH.format(panel_name=self.MANAGED_DEVICE_COVERAGE))

    def find_dashboard_card(self, title):
        return self.driver.find_element_by_xpath(
            self.PANEL_BY_NAME_XPATH.format(panel_name=title))

    def get_lifecycle_tooltip(self):
        return self.driver.find_element_by_css_selector(self.LIFECYCLE_TOOLTIP_CSS)

    @retry(stop_max_delay=10000, wait_fixed=500)
    def hover_over_lifecycle_chart(self):
        sl_card = self.find_system_lifecycle_card()
        sl_cycle = self.get_cycle_from_card(sl_card)
        ActionChains(self.driver).move_to_element(sl_cycle).perform()
        assert self.get_lifecycle_tooltip()

    def hover_over_histogram_bar(self, histogram_chart, index):
        self.hover_over_element(self.get_histogram_bar_from_histogram(histogram_chart, index))

    def hover_over_histogram_title(self, histogram_chart, index):
        self.hover_over_element(self.get_histogram_title_from_histogram(histogram_chart, index))

    def hover_over_histogram_line(self, histogram_chart, index):
        self.hover_over_element(self.get_histogram_line_from_histogram(histogram_chart, index))

    def hover_over_pie_chart_slice(self, pie_chart, index):
        self.hover_over_element(self.get_histogram_line_from_histogram(pie_chart, index))

    def get_tooltip_header_name(self, card):
        return card.find_element_by_css_selector(f'{self.TOOLTIP_HEADER_CONTENT_CSS} .name').text

    def get_tooltip_header_percentage(self, card):
        percentage_element = card.find_element_by_css_selector(f'{self.TOOLTIP_HEADER_CONTENT_CSS} .percentage')
        return self.get_percentage_number(percentage_element.get_attribute('textContent'))

    def get_tooltip_body_name(self, card):
        return card.find_element_by_css_selector(f'{self.TOOLTIP_BODY_CONTENT_CSS} .name').text

    def get_tooltip_body_value(self, card):
        return card.find_element_by_css_selector(f'{self.TOOLTIP_BODY_CONTENT_CSS} .value').text

    def get_tooltip_body_percentage(self, card):
        percentage_element = card.find_element_by_css_selector(f'{self.TOOLTIP_BODY_CONTENT_CSS} .percentage')
        return self.get_percentage_number(percentage_element.get_attribute('textContent'))

    def get_tooltip_body_component_names(self, card):
        return card.find_elements_by_css_selector(f'{self.TOOLTIP_BODY_CONTENT_CSS} .body-component-name')

    @staticmethod
    def get_percentage_number(percentage_text, precision=3):
        getcontext().prec = precision
        result = ''
        match = re.search(r'^\((\d+.\d+)%\)$', percentage_text)
        if match:
            result = Decimal(match.group(1))
        else:
            match = re.search(r'^\((\d+).+$', percentage_text)
            if match:
                result = Decimal(match.group(1))
        return result

    def get_lifecycle_tooltip_table_data(self):
        table_data = []

        lifecycle_table = self.driver.find_element_by_css_selector(self.LIFECYCLE_TABLE_CSS)

        # Use from index 1 to avoid selecting the table head
        rows = lifecycle_table.find_elements_by_tag_name('tr')[1:]
        for row in rows:
            # Get the columns in order [name, status]
            name = row.find_elements_by_tag_name('td')[1].text
            status = row.find_elements_by_tag_name('td')[2].text
            table_data.append({'name': name, 'status': status})

        return table_data

    def get_lifecycle_card_info(self) -> dict:
        """
        {   'System Lifecycle': 'STABLE',
            'Last cycle started at:': '2020-02-05 16:05:00',
            'Last cycle completed at:': '2020-02-05 16:05:13',
            'Next cycle starts in:': '24 hours'
        }
        :return: dict
        """
        sl_card = self.find_system_lifecycle_card()
        assert self.get_title_from_card(sl_card) == self.SYSTEM_LIFECYCLE
        lst = sl_card.text.split('\n')

        return {lst[i].lstrip(): lst[i + 1]
                for i in range(0, len(lst))
                if i < len(lst) and
                lst[i].lstrip().startswith(('System', 'Last', 'Next')) and not
                lst[i + 1].lstrip().startswith(('System', 'Last', 'Next'))}

    def find_system_lifecycle_card(self):
        return self.driver.find_element_by_css_selector('div.x-card.chart-lifecycle.print-exclude')

    def find_new_chart_card(self):
        return self.driver.find_element_by_css_selector(self.NEW_CARD_CHART_CSS)

    def is_new_chart_card_missing(self):
        return len(self.driver.find_elements_by_css_selector(self.NEW_CARD_CHART_CSS)) == 0

    def find_device_discovery_card(self):
        return self.driver.find_elements_by_css_selector('div.x-card.x-discovery-card')[0]

    def find_user_discovery_card(self):
        return self.driver.find_elements_by_css_selector('div.x-card.x-discovery-card')[1]

    def fill_query_value(self, text, parent=None):
        self.fill_text_field_by_css_selector(self.QUERY_SEARCH_INPUT_CSS, text, context=parent)

    def enter_search(self):
        self.key_down_enter(self.find_query_search_input())

    def open_view_devices(self):
        self.click_button('View in Devices', should_scroll_into_view=False)

    def open_view_users(self):
        self.click_button('View in Users', should_scroll_into_view=False)

    def open_new_card_wizard(self):
        """
        fix for flakiness element click, sometimes the click action doesnt work and wont return an error
        or raise exception. try to click on that element until the desire element will appear or raise TimeoutError
        the timeout is 60sec, with 0.5sec interval try 120 clicks (defined in wait_until)
        :return:
        """
        wait_until(func=self.do_open_card_wizard,
                   tolerated_exceptions_list=[NoSuchElementException, ElementClickInterceptedException])

    def do_open_card_wizard(self):
        """
        click on new card wizard and check if the click worked by checking the existence of the modal overlay
        if the click didnt work an NoSuchElementException will be raised
        this function designed to run in wait_until loop, witch expecting the NoSuchElementException exception
        :return: the overlay element of the desired wizard
        """
        new_chart_button = self.wait_for_element_present_by_css(self.NEW_CARD_WIZARD_CSS)
        new_chart_button.click()
        return self.driver.find_element_by_css_selector(self.NEW_CARD_WIZARD_OVERLAY_CSS)

    def select_chart_metric(self, option):
        self.wait_for_element_present_by_css(self.CHART_METRIC_DROP_DOWN_CSS)
        self.select_option_without_search(self.CHART_METRIC_DROP_DOWN_CSS, self.WIZARD_OPTIONS_CSS, option, parent=None)

    def select_chart_view_name(self, view_name, parent=None):
        self.select_option(self.SELECT_VIEW_NAME_CSS,
                           self.DROPDOWN_TEXT_BOX_CSS,
                           self.DROPDOWN_SELECTED_OPTION_CSS,
                           view_name,
                           parent=parent,
                           partial_text=False)

    def select_chart_view_name_by_index(self, view_name, index=0):
        self.select_option_from_multiple(index, self.SELECT_VIEW_NAME_CSS, self.DROPDOWN_TEXT_BOX_CSS,
                                         self.DROPDOWN_SELECTED_OPTION_CSS, view_name)

    def select_intersection_chart_first_query(self, query):
        self.select_option(
            self.INTERSECTION_CHART_FIRST_QUERY_DROP_DOWN_CSS,
            self.DROPDOWN_TEXT_BOX_CSS,
            self.DROPDOWN_SELECTED_OPTION_CSS,
            query,
            parent=None
        )

    def select_intersection_chart_second_query(self, query):
        self.select_option(
            self.INTERSECTION_CHART_SECOND_QUERY_DROP_DOWN_CSS,
            self.DROPDOWN_TEXT_BOX_CSS,
            self.DROPDOWN_SELECTED_OPTION_CSS,
            query,
            parent=None
        )

    def select_matrix_wizard_base_query(self, index, query):
        self.select_option_without_search(self.MATRIX_WIZARD_BASE_QUERY_CSS.format(index=index),
                                          self.WIZARD_OPTIONS_CSS, query, parent=None)

    def select_matrix_wizard_intersecting_query(self, index, query):
        self.select_option_without_search(self.MATRIX_WIZARD_INTERSECTING_QUERY_CSS.format(index=index),
                                          self.WIZARD_OPTIONS_CSS, query, parent=None)

    def select_chart_wizard_module(self, entity, parent=None):
        self.select_option_without_search(self.CHART_MODULE_DROP_DOWN_CSS, self.WIZARD_OPTIONS_CSS,
                                          entity, parent=parent)

    def select_chart_wizard_module_by_index(self, entity, index=0):
        self.select_option_without_search_from_multiple(index, self.CHART_MODULE_DROP_DOWN_CSS, self.WIZARD_OPTIONS_CSS,
                                                        entity)

    def select_chart_wizard_field(self, prop, partial_text=True):
        self.select_option(self.CHART_FIELD_DROP_DOWN_CSS,
                           self.CHART_FIELD_TEXT_BOX_CSS,
                           self.WIZARD_OPTIONS_CSS, prop,
                           parent=None,
                           partial_text=partial_text)

    def get_chart_wizard_field_value(self) -> str:
        wizard_field_picker = self.driver.find_element_by_css_selector(self.CHART_FIELD_DROP_DOWN_CSS)
        return wizard_field_picker.find_element_by_css_selector(self.CHART_DROPDOWN_FIELD_VALUE_CSS).text

    def select_chart_wizard_datepicker(self, child_index=2, date_value=datetime.datetime.now(), parent=None):
        self.fill_text_field_by_css_selector(self.CHART_WIZARD_DATEPICKER_CSS.format(child_index=child_index),
                                             date_value.isoformat(), context=parent)
        # Sleep through the time it takes the date picker to react to the filled date
        time.sleep(0.5)

    def select_chart_wizard_adapter(self, prop, partial_text=True):
        self.select_option(self.CHART_ADAPTER_DROP_DOWN_CSS,
                           self.CHART_FIELD_TEXT_BOX_CSS,
                           self.WIZARD_OPTIONS_CSS, prop,
                           parent=None,
                           partial_text=partial_text)

    def select_chart_result_range_last(self):
        self.driver.find_element_by_css_selector(self.CHART_TIMELINE_LAST_RANGE_RADIO_CSS).click()

    def select_chart_result_range_date(self):
        self.driver.find_element_by_css_selector(self.CHART_TIMELINE_DATE_RANGE_RADIO_CSS).click()

    def toggle_comparison_intersection_switch(self):
        self.driver.find_element_by_css_selector(self.CHART_WIZARD_TYPE_SWITCH_CSS).click()

    def select_chart_summary_function(self, func_name):
        self.select_option_without_search(self.CHART_FUNCTION_CSS, self.WIZARD_OPTIONS_CSS, func_name, parent=None)

    def find_chart_segment_include_empty(self):
        return self.find_checkbox_with_label_by_label('Include entities with no value')

    def check_chart_segment_include_empty(self):
        self.find_chart_segment_include_empty().click()

    def is_chart_segment_include_empty_enabled(self):
        checkbox = self.find_checkbox_with_label_by_label('Include entities with no value')
        return checkbox.find_element_by_css_selector('input').is_enabled()

    def fill_chart_segment_filter(self, value_name, value_filter, list_position=1):
        self.select_option_without_search(
            self.SEGMENTATION_FILTER_DROP_DOWN_CSS.format(index=list_position),
            self.WIZARD_OPTIONS_CSS,
            value_name,
            parent=None)
        self.fill_text_field_by_css_selector(
            f'{self.CHART_WIZARD_CSS} {self.SEGMENTATION_FILTER_INPUT_CSS.format(index=list_position)}', value_filter)

    def add_chart_segment_filter_row(self):
        self.driver.find_element_by_css_selector(self.SEGMENTATION_ADD_FILTER_BUTTON_CSS).click()

    def is_add_chart_segment_filter_button_disabled(self):
        return self.is_element_disabled(
            self.driver.find_element_by_css_selector(self.SEGMENTATION_ADD_FILTER_BUTTON_CSS)
        )

    def remove_chart_segment_filter(self, list_position=1):
        self.driver.find_element_by_css_selector(
            self.SEGMENTATION_FILTER_DELETE_CSS.format(index=list_position)).click()

    def get_views_list(self):
        return self.wait_for_element_present_by_css(self.SELECT_VIEWS_CSS).find_elements_by_css_selector(
            self.SELECT_VIEWS_VIEW_CSS)

    def get_views_list_add_button(self):
        return self.driver.find_element_by_id(self.SELECT_VIEWS_ADD_BUTTON)

    def prepare_comparison_card(self, module_query_list, title, chart_type='histogram',
                                sort_by='value', sort_order='desc'):
        self.open_new_card_wizard()
        self.select_chart_metric('Query Comparison')
        views_list = self.get_views_list()
        self.driver.find_element_by_css_selector(f'#{chart_type}').click()

        for index, module_query in enumerate(module_query_list):
            if index > 1:
                self.get_views_list_add_button().click()
            if module_query['module'] != '':
                self.select_chart_wizard_module_by_index(module_query['module'], index)
            if module_query['query'] != '':
                self.select_chart_view_name_by_index(module_query['query'], index)

        self.fill_text_field_by_element_id(self.CHART_TITLE_ID, title)

        if chart_type == 'histogram':
            self.driver.find_element_by_css_selector(self.WIZARD_SORT_BY.format(sort_by=sort_by)).click()
            self.driver.find_element_by_css_selector(self.WIZARD_SORT_ORDER.format(sort_order=sort_order)).click()

    def add_comparison_card(self, module_query_list, title, chart_type='histogram', sort_by='value', sort_order='desc'):
        self.prepare_comparison_card(module_query_list, title, chart_type, sort_by, sort_order)
        self.click_card_save()
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS, interval=1)
        self.wait_for_card_spinner_to_end()

    def add_comparison_card_view(self, module, query):
        self.click_button('+', context=self.driver.find_element_by_css_selector(self.CHART_WIZARD_CSS))
        views_list = self.get_views_list()
        self.select_chart_wizard_module(module, views_list[2])
        self.select_chart_view_name(query, views_list[2])
        self.click_card_save()
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS, interval=1)
        self.wait_for_card_spinner_to_end()

    def add_intersection_card(self, module, first_query, second_query, title, view_name=''):
        self.open_new_card_wizard()
        self.select_chart_metric('Query Intersection')
        self.select_chart_wizard_module(module)
        if view_name:
            self.select_chart_view_name(view_name)
        self.select_intersection_chart_first_query(first_query)
        self.select_intersection_chart_second_query(second_query)
        self.fill_text_field_by_element_id(self.CHART_TITLE_ID, title)
        self.click_card_save()
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS, interval=1)
        self.wait_for_card_spinner_to_end()

    def add_summary_card(self, module, field, func_name, title):
        self.open_new_card_wizard()
        self.select_chart_metric('Field Summary')
        self.select_chart_wizard_module(module)
        self.select_chart_wizard_field(field)
        self.select_chart_summary_function(func_name)
        self.fill_text_field_by_element_id(self.CHART_TITLE_ID, title)
        self.click_card_save()

    def add_timeline_card(self, module, view, title):
        self.open_new_card_wizard()
        self.fill_text_field_by_element_id(self.CHART_TITLE_ID, title)
        self.select_chart_metric('Query Timeline')
        self.select_chart_wizard_module(module)
        self.select_chart_view_name(view)
        self.click_card_save()

    def add_matrix_card(self, module, title, base_queries, intersecting_queries, sort_by='value', sort_order='desc'):
        self.switch_to_page()
        self.open_new_card_wizard()
        self.fill_text_field_by_element_id(self.CHART_TITLE_ID, title)
        self.select_chart_metric('Matrix Data')
        self.select_chart_wizard_module(module)

        if base_queries[0]:
            self.select_matrix_wizard_base_query(1, base_queries[0])
        base_query_count = len(base_queries)
        if base_query_count > 1:
            for index in range(2, base_query_count + 1):
                self.add_matrix_wizard_base_query()
                query = base_queries[index - 1]
                if query:
                    self.select_matrix_wizard_base_query(index, query)

        self.select_matrix_wizard_intersecting_query(1, intersecting_queries[0])
        intersecting_query_count = len(intersecting_queries)
        if intersecting_query_count > 1:
            for index in range(2, intersecting_query_count + 1):
                self.add_matrix_wizard_intersecting_query()
                query = intersecting_queries[index - 1]
                self.select_matrix_wizard_intersecting_query(index, query)

        self.driver.find_element_by_css_selector(self.WIZARD_SORT_BY.format(sort_by=sort_by)).click()
        self.driver.find_element_by_css_selector(self.WIZARD_SORT_ORDER.format(sort_order=sort_order)).click()

        self.click_card_save()
        return self.get_card(title)

    def add_matrix_wizard_base_query(self):
        self.driver.find_element_by_css_selector(self.MATRIX_WIZARD_ADD_BASE_QUERY_CSS).click()

    def add_matrix_wizard_intersecting_query(self):
        self.driver.find_element_by_css_selector(self.MATRIX_WIZARD_ADD_INTERSECTING_QUERY_CSS).click()

    def get_matrix_chart_group_names(self, card):
        return [group.text for group in card.find_elements_by_css_selector(self.MATRIX_GROUP_NAME_CSS)]

    def get_matrix_chart_group_values(self, card):
        return [int(group.text) for group in card.find_elements_by_css_selector(self.MATRIX_GROUP_TOTAL_CSS)]

    def get_matrix_chart_group_slices(self, card, index):
        group = card.find_elements_by_css_selector(self.MATRIX_GROUP_CSS)[index]
        return group.find_elements_by_css_selector(self.MATRIX_GROUP_SLICES)

    def get_matrix_chart_total_value(self, card):
        return card.find_element_by_css_selector(self.MATRIX_TOTAL_COUNT_CSS).text

    def click_card_save(self):
        self.get_enabled_button('Save').click()
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS, interval=1)
        self.wait_for_card_spinner_to_end()

    def is_card_save_button_disabled(self):
        return self.is_save_button_disabled()

    def add_segmentation_card(self, module, field, title, chart_type='histogram', view_name='', partial_text=True,
                              include_empty: bool = True, value_filter: str = '', sort_config=None):

        if sort_config is None:
            sort_by = 'value'
            sort_order = 'desc'
        else:
            sort_by = sort_config.get('sort_by', 'value')
            sort_order = sort_config.get('sort_order', 'desc')

        try:
            self.open_new_card_wizard()
            self.select_chart_metric('Field Segmentation')
            self.driver.find_element_by_css_selector(f'#{chart_type}').click()
            self.select_chart_wizard_module(module)
            if view_name:
                self.select_chart_view_name(view_name)
            self.select_chart_wizard_field(field, partial_text)
            if include_empty:
                self.check_chart_segment_include_empty()
            if value_filter:
                self.fill_chart_segment_filter(field, value_filter)
            self.fill_text_field_by_element_id(self.CHART_TITLE_ID, title)

            if chart_type == 'histogram':
                self.driver.find_element_by_css_selector(self.WIZARD_SORT_BY.format(sort_by=sort_by)).click()
                self.driver.find_element_by_css_selector(self.WIZARD_SORT_ORDER.format(sort_order=sort_order)).click()

            self.click_card_save()
            self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS, interval=1)
            self.wait_for_card_spinner_to_end()
        except NoSuchElementException:
            self.close_dropdown()
            self.click_button('Cancel')
            self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS)
            return False
        return True

    def create_and_get_paginator_segmentation_card(self, run_discovery, module, field, title, view_name, sort=None):
        self.switch_to_page()
        if run_discovery:
            self.run_discovery()
        self.add_segmentation_card(module=module,
                                   field=field,
                                   title=title,
                                   view_name=view_name,
                                   partial_text=False,
                                   sort_config=sort)
        # create reference to the segmentation card with title
        segmentation_card = self.get_card(title)
        # create reference to the histogram within the card
        return self.get_histogram_chart_from_card(segmentation_card)

    def get_summary_card_text(self, card_title):
        return self.wait_for_element_present_by_css(self.SUMMARY_CARD_TEXT_CSS,
                                                    element=self.driver.find_element_by_xpath(
                                                        self.PANEL_BY_NAME_XPATH.format(panel_name=card_title)))

    def get_card(self, card_title):
        return self.wait_for_element_present_by_css(f'.card-container-outer[name="{card_title}"]')

    def get_card_id(self, card_title):
        return self.get_card(card_title).get_attribute('id')

    def get_all_cards(self):
        return self.driver.find_elements_by_css_selector('.x-tab.active div.x-card')

    def get_last_card_created(self):
        return self.driver.find_elements_by_css_selector('.x-card.card__item')[-1]

    def click_segmentation_pie_card(self, card_title):
        card = self.get_card(card_title)
        pie = self.get_pie_chart_from_card(card)
        pie.find_element_by_css_selector('svg').click()

    def is_edit_card_button_present(self, card_title):
        panel = self.wait_for_element_present_by_xpath(self.PANEL_BY_NAME_XPATH.format(panel_name=card_title))
        if len(panel.find_elements_by_css_selector(self.CARD_MENU_BTN_CSS)) == 0:
            return False
        self.open_close_card_menu(panel)
        edit_buttons = self.driver.find_elements_by_id(self.CARD_EDIT_BTN_ID)
        result = False
        for button in edit_buttons:
            if button.is_displayed():
                result = True
        self.open_close_card_menu(panel)
        return result

    def edit_card(self, card_title):
        panel = self.get_card(card_title)
        self.open_close_card_menu(panel)
        self.driver.find_element_by_id(self.CARD_EDIT_BTN_ID).click()
        self.wait_for_element_present_by_css(self.MODAL_OVERLAY_CSS)
        self.wait_for_card_spinner_to_end()

    def open_edit_card(self, card):
        self.open_close_card_menu(card)
        self.driver.find_element_by_id(self.CARD_EDIT_BTN_ID).click()
        self.wait_for_element_present_by_css(self.MODAL_OVERLAY_CSS)
        self.wait_for_card_spinner_to_end()

    def is_remove_card_button_present(self, card_title):
        panel = self.wait_for_element_present_by_xpath(self.PANEL_BY_NAME_XPATH.format(panel_name=card_title))
        if len(panel.find_elements_by_css_selector(self.CARD_MENU_BTN_CSS)) == 0:
            return False
        self.open_close_card_menu(panel)
        remove_buttons = self.driver.find_elements_by_id(self.CARD_CLOSE_BTN_ID)
        result = False
        for button in remove_buttons:
            if button.is_displayed():
                result = True
        self.open_close_card_menu(panel)
        return result

    def remove_card(self, card_title):
        panel = self.get_card(card_title)
        self.open_close_card_menu(panel)
        self.driver.find_element_by_id(self.CARD_CLOSE_BTN_ID).click()
        self.wait_for_element_present_by_css(self.MODAL_OVERLAY_CSS)
        self.click_button(self.CARD_CLOSE_BTN_TEXT)
        wait_until(lambda: self.is_missing_panel(card_title))

    def export_card(self, card_title):
        panel = self.get_card(card_title)
        self.open_close_card_menu(panel)
        self.driver.find_element_by_id('export_chart').click()

    def refresh_card(self, card_title):
        panel = self.get_card(card_title)
        self.open_close_card_menu(panel)
        self.driver.find_element_by_id('refresh_chart').click()

    def open_close_card_menu(self, panel):
        panel.find_element_by_css_selector(self.CARD_MENU_BTN_CSS).click()
        time.sleep(0.5)  # wait for menu to open or close

    def close_card_menu(self, panel):
        el = panel.find_element_by_css_selector(self.CARD_MENU_BTN_CSS)
        ActionChains(self.driver).move_to_element_with_offset(el, 50, 100).click().perform()

    def open_move_or_copy_card(self, card_title, copy=True):
        panel = self.get_card(card_title)
        self.open_close_card_menu(panel)
        self.driver.find_element_by_id('move_or_copy_chart').click()
        self.wait_for_element_present_by_css('.ant-modal')
        time.sleep(0.4)  # Wait for opening animation to end

    def select_space_for_move_or_copy(self, text_option):
        self.driver.find_element_by_id(self.MOVE_OR_COPY_SPACE_SELECT_ID).click()
        dropdown = self.driver.find_element_by_css_selector(self.MOVE_OR_COPY_SPACE_DROPDOWN_CSS)
        self.find_element_by_text(text_option, element=dropdown).click()

    def get_all_spaces_for_move_or_copy(self):
        self.driver.find_element_by_id(self.MOVE_OR_COPY_SPACE_SELECT_ID).click()
        return self.get_all_select_options(self.MOVE_OR_COPY_SPACE_DROPDOWN_CSS,
                                           self.MOVE_OR_COPY_SPACE_DROPDOWN_ITEM_CSS)

    def find_move_or_copy_checkbox(self):
        return self.driver.find_element_by_id('create_panel_copy')

    def toggle_move_or_copy_checkbox(self):
        return self.find_move_or_copy_checkbox().click()

    def is_move_or_copy_checkbox_disabled(self):
        return self.is_element_disabled(self.find_move_or_copy_checkbox())

    def close_move_or_copy_dialog(self):
        self.get_cancel_button(self.driver.find_element_by_id(self.MOVE_OR_COPY_MODAL_ID)).click()
        self.wait_for_move_or_copy_dialog_to_be_absent()

    def wait_for_move_or_copy_dialog_to_be_absent(self):
        self.wait_for_element_absent_by_id(self.MOVE_OR_COPY_MODAL_ID)

    def find_search_insights(self):
        return self.driver.find_element_by_css_selector(self.SEARCH_INSIGHTS_CSS)

    def find_query_search_input(self):
        return self.driver.find_element_by_css_selector(self.QUERY_SEARCH_INPUT_CSS)

    def change_chart_type(self, chart_type):
        self.driver.find_element_by_css_selector(f'#{chart_type}').click()

    def get_pie_slices_data(self, pie):
        """
        get the numbers from pie chart slices
        :param pie: the pie chart
        :return: list of all slices data as text
        """
        pie_data = []
        pie_slices = pie.find_elements_by_css_selector(self.PIE_SLICE_CSS)
        for pie_slice in pie_slices:
            value = pie_slice.text.rstrip('%')
            if value:
                pie_data.append(value)

        return pie_data

    def assert_pie_slices_data(self, card, data_list):
        pie = self.get_pie_chart_from_card(card)
        pie_data = self.get_pie_slices_data(pie)
        assert pie_data == data_list

    def assert_histogram_lines_data(self, card, data_list):
        histogram = self.get_histogram_chart_from_card(card)
        histogram_data = self.get_histogram_lines_data(histogram)
        assert histogram_data == data_list

    def assert_summary_text_data(self, card, data_list):
        title = self.get_title_from_card(card)
        summary_data = [self.get_summary_card_text(title).text]
        assert summary_data == data_list

    def assert_timeline_svg_exist(self, card):
        time.sleep(2)
        assert card.find_element_by_css_selector(self.TEST_TIMELINE_SVG_CSS)

    @staticmethod
    def assert_data_devices_fit_pagination_data(histogram_items_title, host_names_list):
        # Checking the lists are equal by one sided containment + equal length
        assert len(histogram_items_title) == len(host_names_list)
        assert all(item in host_names_list for item in histogram_items_title)

    def get_uncovered_from_pie(self, pie):
        return int(pie.find_element_by_css_selector(self.UNCOVERED_PIE_SLICE_CSS).text.rstrip('%'))

    def get_covered_from_pie(self, pie):
        return int(pie.find_element_by_css_selector(self.COVERED_PIE_SLICE_CSS).text.rstrip('%'))

    def click_uncovered_pie_slice(self, xoffset=10, yoffset=10):
        self.click_pie_slice(self.UNCOVERED_PIE_SLICE_CSS, self.MANAGED_DEVICE_COVERAGE, xoffset, yoffset)

    def click_covered_pie_slice(self):
        self.click_pie_slice(self.COVERED_PIE_SLICE_CSS, self.MANAGED_DEVICE_COVERAGE)

    def click_intersection_pie_slice(self, card_title):
        self.click_pie_slice(self.INTERSECTION_PIE_INTERSECTION_SLICE_CSS, card_title)

    def click_symmetric_difference_base_query_pie_slice(self, card_title):
        self.click_pie_slice(self.SYMMETRIC_DIFFERENCE_FROM_BASE_QUERY_SLICE_CSS, card_title)

    def click_symmetric_difference_first_query_pie_slice(self, card_title):
        self.click_pie_slice(self.SYMMETRIC_DIFFERENCE_FROM_FIRST_QUERY_SLICE_CSS, card_title)

    def click_pie_slice(self, slice_css, card_title, xoffset=10, yoffset=10):
        card = self.get_card(card_title)
        time.sleep(1.2)
        self.scroll_into_view_js(card)
        if xoffset and yoffset:
            el = self.get_pie_chart_from_card(card).find_element_by_css_selector(slice_css)
            ActionChains(self.driver).move_to_element_with_offset(el, xoffset, yoffset).click().perform()
            return
        self.get_pie_chart_from_card(card).find_element_by_css_selector(slice_css).click()

    @staticmethod
    def get_title_from_card(card):
        return card.find_element_by_css_selector('div.header div.card-title').text.title()

    @staticmethod
    def get_pie_chart_from_card(card):
        return card.find_element_by_css_selector('div.x-pie')

    @staticmethod
    def get_histogram_chart_from_card(card):
        return card.find_element_by_css_selector('.x-histogram')

    def get_histogram_chart_by_title(self, histogram_title):
        return self.get_card(histogram_title).find_element_by_css_selector('.x-histogram')

    @staticmethod
    def get_card_pagination_text(card):
        return card.find_element_by_css_selector('.paginator-text').text

    @staticmethod
    def get_histogram_line_from_histogram(histogram, number):
        return histogram.find_element_by_css_selector(f'div:nth-child({number}) > .item-bar div.quantity')

    @staticmethod
    def get_histogram_bar_from_histogram(histogram, number):
        return histogram.find_element_by_css_selector(f'div:nth-child({number}) > .item-bar div.bar.growing-x')

    @staticmethod
    def get_histogram_title_from_histogram(histogram, number):
        return histogram.find_element_by_css_selector(f'div:nth-child({number}) > div.item-title')

    def get_count_histogram_lines_from_histogram(self, histogram):
        return len(histogram.find_elements_by_css_selector(self.HISTOGRAM_ITEMS))

    def get_histogram_items_on_pagination(self, histogram):
        return histogram.find_elements_by_css_selector(self.HISTOGRAM_ITEMS)

    def get_histogram_current_page_item_titles(self, histogram):
        histogram_items_title = []
        histogram_items = self.get_histogram_items_on_pagination(histogram)
        for line_item in histogram_items:
            histogram_items_title.append(line_item.find_element_by_css_selector('.item-title').text)
        return histogram_items_title

    def get_histogram_items_quantities_on_pagination(self, histogram):
        histogram_items = self.get_histogram_items_on_pagination(histogram)
        for line_item in histogram_items:
            yield line_item.find_element_by_css_selector('.item-bar div.quantity').text

    def get_histogram_lines_data(self, histogram):
        count = self.get_count_histogram_lines_from_histogram(histogram)
        histogram_data = []
        for i in range(count):
            histogram_data.append(self.get_histogram_line_from_histogram(histogram, i + 1).text)
        return histogram_data

    @staticmethod
    def get_pie_chart_slices(pie_chart):
        return pie_chart.find_elements_by_css_selector('.wrapper svg g text')

    @staticmethod
    def get_pie_chart_legend_rows_data(pie_chart):
        legend_grid_cells = pie_chart.find_elements_by_css_selector('.x-chart-legend .legend-grid *')

        rows_data = []
        for i in range(0, len(legend_grid_cells), 4):
            row_data = {'name_element': legend_grid_cells[i + 1], 'name': legend_grid_cells[i + 1].text,
                        'value': legend_grid_cells[i + 2].text, 'percentage': legend_grid_cells[i + 3].text}
            rows_data.append(row_data)
        return rows_data

    def get_paginator_num_of_items(self, histogram):
        return histogram.find_element_by_css_selector(self.PAGINATOR_NUM_OF_ITEMS).text

    def get_paginator_total_num_of_items(self, histogram):
        return histogram.find_element_by_css_selector(self.PAGINATOR_TOTAL_NUM_OF_ITEMS).text

    def get_paginator_from_item_number(self, histogram):
        return histogram.find_element_by_css_selector(self.PAGINATOR_FROM_VALUE).text

    def get_paginator_to_item_number(self, histogram, page_number):
        if page_number == 1:
            to_val = self.PAGINATOR_LIMIT
        else:
            to_val = self.PAGINATOR_TO
        return histogram.find_element_by_css_selector(f'{self.PAGINATOR_CLASS} {to_val}').text

    @staticmethod
    def calculate_from_item_value(num_of_items, num_of_pages, curr_page, to_val, limit):
        if num_of_items % limit != 0 and curr_page == num_of_pages:
            return num_of_items - (num_of_items % limit) + 1
        return to_val - limit + 1

    @staticmethod
    def calculate_to_item_value(num_of_items, page_number, limit):
        if limit > num_of_items:
            return num_of_items
        return min(page_number * limit, num_of_items)

    def get_first_page_button_in_paginator(self, histogram):
        return histogram.find_element_by_css_selector(self.PAGINATOR_FIRST_PAGE_BUTTON)

    def get_previous_page_button_in_paginator(self, histogram):
        return histogram.find_element_by_css_selector(self.PAGINATOR_PREVIOUS_PAGE_BUTTON)

    def get_next_page_button_in_paginator(self, histogram):
        return histogram.find_element_by_css_selector(self.PAGINATOR_NEXT_PAGE_BUTTON)

    def get_last_page_button_in_paginator(self, histogram):
        return histogram.find_element_by_css_selector(self.PAGINATOR_LAST_PAGE_BUTTON)

    def click_to_next_page(self, histogram):
        self.get_next_page_button_in_paginator(histogram).click()

    def click_to_previous_page(self, histogram):
        self.get_previous_page_button_in_paginator(histogram).click()

    def click_to_first_page(self, histogram):
        self.get_first_page_button_in_paginator(histogram).click()

    def click_to_last_page(self, histogram):
        self.get_last_page_button_in_paginator(histogram).click()

    def click_on_histogram_item(self, histogram, item_number):
        histogram.find_element_by_css_selector(f'{self.HISTOGRAM_ITEMS}:nth-child({item_number})').click()

    def get_histogram_bar_item_title(self, histogram, item_number):
        return histogram.find_element_by_css_selector(
            f'{self.HISTOGRAM_ITEMS}:nth-child({item_number}) div.item-title').text

    def check_paginator_buttons_state(self, histogram, first, previous, next_r, last):
        paginator_current_buttons_state = [
            self.is_element_disabled(self.get_first_page_button_in_paginator(histogram)),
            self.is_element_disabled(self.get_previous_page_button_in_paginator(histogram)),
            self.is_element_disabled(self.get_next_page_button_in_paginator(histogram)),
            self.is_element_disabled(self.get_last_page_button_in_paginator(histogram)),
        ]
        paginator_state_buttons_to_validate = [first, previous, next_r, last]
        return paginator_current_buttons_state == paginator_state_buttons_to_validate

    def is_missing_paginator_navigation(self, histogram):
        try:
            histogram.find_elements_by_css_selector(self.PAGINATOR_BUTTON)
        except NoSuchElementException:
            # Good, it is missing
            return True
        return False

    def is_missing_paginator_from_item(self, histogram):
        try:
            histogram.find_element_by_css_selector(self.PAGINATOR_FROM_VALUE)
        except NoSuchElementException:
            # Good, it is missing
            return True
        return False

    def is_missing_paginator_to_item(self, histogram):
        try:
            histogram.find_element_by_css_selector(self.PAGINATOR_TO_VALUE)
        except NoSuchElementException:
            # Good, it is missing
            return True
        return False

    def is_missing_paginator_num_of_items(self, histogram):
        try:
            histogram.find_element_by_css_selector(f'{self.PAGINATOR_CLASS} {self.PAGINATOR_LIMIT}')
        except NoSuchElementException:
            # Good, it is missing
            return True
        return False

    @staticmethod
    def get_cycle_from_card(card):
        return card.find_element_by_css_selector('svg.x-cycle')

    @staticmethod
    def assert_check_in_cycle(cycle):
        assert cycle.find_element_by_css_selector('path.check')

    @staticmethod
    def assert_cycle_is_stable(cycle):
        assert cycle.find_element_by_css_selector('text.cycle-title').text == 'STABLE'

    @staticmethod
    def assert_cycle_start_and_finish_dates(card):
        dates = card.find_elements_by_css_selector('.cycle-date')
        date_start = datetime.datetime.strptime(dates[0].text.strip(), '%Y-%m-%d %H:%M:%S')
        date_finish = datetime.datetime.strptime(dates[1].text.strip(), '%Y-%m-%d %H:%M:%S')
        assert date_finish > date_start

    @staticmethod
    def assert_next_cycle_start(card, text):
        next_time = card.find_element_by_css_selector('.cycle-next-time')
        assert next_time == text

    @staticmethod
    def assert_plus_button_in_card(card):
        assert card.find_element_by_css_selector('.x-button.ant-btn-link').text == '+'

    @staticmethod
    def assert_plus_button_disabled_in_card(card):
        assert card.find_element_by_css_selector('.x-button.ant-btn-link.disabled').text == '+'

    @staticmethod
    def find_adapter_in_card(card, adapter):
        return card.find_element_by_css_selector(f'div[name={adapter}]')

    @staticmethod
    def find_quantity_in_card_string(card):
        return [x.text for x in card.find_elements_by_css_selector('div.quantity') if x.text]

    @staticmethod
    def find_quantity_in_card_int(card):
        data = [x.text for x in card.find_elements_by_css_selector('div.quantity') if x.text]
        translator = str.maketrans(dict.fromkeys('()'))
        translated_data = [[int(s) for s in line.translate(translator).split(' ')] for line in data]
        for item in translated_data:
            if len(item) == 1:
                item.append(0)
        return translated_data

    def find_no_trial_banner(self):
        self.wait_for_element_absent_by_css(self.TRIAL_BANNER_CSS)

    def wait_for_trial_banner(self):
        self.wait_for_element_present_by_css(self.TRIAL_BANNER_CSS)

    def try_to_find_trial_banner(self):
        self.driver.find_element_by_css_selector(self.TRIAL_BANNER_CSS)

    def find_banner_no_contract(self):
        self.wait_for_element_absent_by_css(self.BANNER_NO_CONTRACT_CLASS)

    def find_trial_remainder_banner(self, remainder_count):
        msg = 'days remaining in your Axonius evaluation'
        # Expected color of the banner according UIs thresholds
        color = '231, 76, 60' if (remainder_count <= 7) else (
            '255, 166, 0' if remainder_count <= 14 else '52, 152, 219')
        try:
            banner = self.wait_for_element_present_by_xpath(
                self.BANNER_BY_TEXT_XPATH.format(banner_text=f'{remainder_count} {msg}'))
        except TimeoutException:
            # Currently there is a bug, probably if it is running in midnight AX-3730
            banner = self.wait_for_element_present_by_xpath(
                self.BANNER_BY_TEXT_XPATH.format(banner_text=f'{remainder_count + 1} {msg}'))
        assert banner.value_of_css_property('background-color') == f'rgba({color}, 1)'
        return banner

    def find_contract_remainder_banner(self, remainder_count):
        # Expected color of the banner according UIs thresholds
        color = self.COLOR_VERYDANGEROUS if (remainder_count < 4) else (
            self.COLOR_DANGEROUS if remainder_count < 16 else self.COLOR_INFO)

        banner = self.wait_for_element_present_by_css(self.BANNER_BY_CSS)
        assert Color.from_string(banner.value_of_css_property('background-color')).hex.upper() == color.upper()
        return banner

    def find_trial_expired_banner(self):
        return self.wait_for_element_present_by_text(
            'Axonius evaluation period has expired. Please reach out to your Account Manager.')

    def find_contract_expired_banner(self):
        return self.wait_for_element_present_by_css(self.BANNER_BY_CSS).text.\
            startswith('Your Axonius subscription has expired')

    def find_active_space_header_title(self):
        return self.driver.find_element_by_xpath(self.ACTIVE_SPACE_HEADERS_XPATH).text

    def open_space_action_menu(self):
        self.driver.find_element_by_css_selector(self.SPACE_ACTION_MENU_CSS).click()

    def find_space_header(self, index=1):
        return self.find_elements_by_xpath(self.SPACE_HEADERS_XPATH)[index - 1]

    def find_space_header_title(self, index=1):
        return self.find_space_header(index).find_element_by_tag_name('div').text

    def save_space_name(self, space_name, space_roles=None):
        name_input = self.wait_for_element_present_by_id(self.RENAME_SPACE_INPUT_ID)
        self.fill_text_by_element(name_input, space_name)
        if space_roles:
            radio_button = self.wait_for_element_present_by_css(f'#{self.SPACE_ACCESS_RADIO_BUTTON_ID}')
            radio_button.click()
            self.select_multiple_option_without_search(self.SPACE_ROLES_SELECT_ID,
                                                       self.ANT_SELECT_MENU_ITEM_CSS, space_roles)

        self.click_ant_button(self.SAVE_BUTTON)
        self.wait_for_modal_close()

    def find_add_space(self):
        return self.driver.find_element_by_xpath(self.NEW_SPACE_BUTTON_XPATH)

    def wait_add_space(self):
        return self.wait_for_element_present_by_xpath(self.NEW_SPACE_BUTTON_XPATH)

    def add_new_space(self, space_name, space_roles=None):
        self.wait_add_space().click()
        self.save_space_name(space_name, space_roles)

    def is_missing_add_space(self):
        try:
            self.find_add_space()
        except NoSuchElementException:
            # Good, indeed missing
            return True
        return False

    def select_space(self, index=0):
        space_header = self.find_space_header(index)
        space_header.click()
        # make sure space loaded
        self.wait_for_element_absent_by_css('.x-card .chart-new')
        return space_header

    def edit_space(self, space_name, space_roles=None, index=2, ):
        # Default 2 since 1 is not renamable
        self.select_space(index)
        self.open_space_action_menu()
        self.driver.find_element_by_id(self.EDIT_SPACE_MENU_ITEM_ID).click()
        self.save_space_name(space_name, space_roles)

    def assert_disabled_space_menu(self, index=3):
        # Default 4 since 1 and 2 are not renamable
        self.select_space(index)
        with pytest.raises(TimeoutException):
            self.wait_for_element_present_by_css(self.SPACE_ACTION_MENU_CSS)

    def is_missing_remove_space(self, index=3):
        # Default 3 since 1 and 2 are note removable
        self.select_space(index)
        self.open_space_action_menu()
        return len(self.driver.find_elements_by_id(self.REMOVE_SPACE_MENU_ITEM_ID)) == 0

    def remove_space(self, index=3):
        # Default 3 since 1 and 2 are note removable
        space_header = self.select_space(index)
        space_header_text = space_header.text
        self.open_space_action_menu()
        self.driver.find_element_by_id(self.REMOVE_SPACE_MENU_ITEM_ID).click()
        self.wait_for_element_present_by_css(self.DIALOG_OVERLAY_CSS)
        self.click_button(self.SPACE_DELETE_BTN_TEXT)
        self.wait_for_element_absent_by_text(space_header_text)

    def is_missing_space(self, space_name):
        try:
            self.find_element_by_text(space_name)
        except NoSuchElementException:
            # Good, we want it gone
            return True
        return False

    def is_missing_panel(self, panel_name):
        try:
            self.driver.find_element_by_xpath(self.PANEL_BY_NAME_XPATH.format(panel_name=panel_name))
        except NoSuchElementException:
            # Good, it is missing
            return True
        return False

    def find_no_data_label(self):
        return self.wait_for_element_present_by_text(self.NO_DATA_FOUND_TEXT)

    def is_chart_save_disabled(self) -> bool:
        return self.is_element_disabled_by_id('chart_save')

    def fill_current_chart_title(self, value):
        self.fill_text_field_by_element_id(self.CHART_TITLE_ID, value)

    def wait_for_card_spinner_to_end(self):
        # This method wants to wait for the card spinner to appear and finish.

        # It's impossible to wait for the card spinner to begin
        # because it might already be gone when we got here, so we optimistically
        # wait a bit to simulate waiting for the spinner to appear.
        time.sleep(0.3)

        self.wait_for_element_absent_by_css(self.CARD_SPINNER_CSS)

    def click_card_cancel(self):
        self.click_button('Cancel')
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS, interval=1)

    def toggle_chart_wizard_module(self, selector_element_css=CHART_MODULE_DROP_DOWN_CSS,
                                   ddl_selector_css=CHART_MODULE_DROP_DOWN_CSS,
                                   options_css=WIZARD_OPTIONS_CSS,
                                   parent=None):

        module = self.driver.find_element_by_css_selector(selector_element_css)

        if module.text == 'Devices':
            self.select_option_without_search(text='Users',
                                              dropdown_css_selector=ddl_selector_css,
                                              selected_options_css_selector=options_css,
                                              parent=parent)
        else:
            self.select_option_without_search(text='Devices',
                                              dropdown_css_selector=ddl_selector_css,
                                              selected_options_css_selector=options_css,
                                              parent=parent)

    def assert_intersection_chart_first_query_default(self):
        select = self.driver.find_element_by_css_selector(self.INTERSECTION_CHART_FIRST_QUERY_DROP_DOWN_CSS)
        assert select.text == self.CHART_QUERY_DEFAULT

    def assert_intersection_chart_secound_query_default(self):
        select = self.driver.find_element_by_css_selector(self.INTERSECTION_CHART_SECOND_QUERY_DROP_DOWN_CSS)
        assert select.text == self.CHART_QUERY_DEFAULT

    def assert_summary_chart_query_filter_default(self):
        select = self.driver.find_element_by_css_selector(self.CARD_FILTER_CSS)
        assert select.text == self.CHART_QUERY_ALL_DEFAULT

    def assert_summary_chart_query_field_default(self):
        select = self.driver.find_element_by_css_selector(self.CARD_FIELD_CSS)
        assert select.text == self.CHART_QUERY_FIELD_DEFAULT

    def assert_compression_chart_first_query_field_default(self):
        select = self.driver.find_element_by_css_selector(self.COMPARISON_CARD_1ST_QUERY_CSS)
        assert select.text == self.CHART_QUERY_DEFAULT

    def assert_compression_chart_second_query_field_default(self):
        select = self.driver.find_element_by_css_selector(self.COMPARISON_CARD_2ND_QUERY_CSS)
        assert select.text == self.CHART_QUERY_DEFAULT

    def assert_segmentation_chart_query_field_default(self):
        select = self.driver.find_element_by_css_selector(self.SELECT_VIEW_NAME_CSS)
        assert select.text == self.CHART_QUERY_ALL_DEFAULT

    def assert_segmentation_chart_field_default(self):
        select = self.driver.find_element_by_css_selector(self.CHART_FIELD_DROP_DOWN_CSS)
        assert select.text == self.CHART_QUERY_FIELD_DEFAULT

    def verify_card_config_reset_intersection_chart(self, chart_title):
        self.edit_card(chart_title)
        try:
            self.toggle_chart_wizard_module()
            self.assert_intersection_chart_first_query_default()
            self.assert_intersection_chart_secound_query_default()
        finally:
            self.click_card_cancel()

    def verify_card_config_reset_summary_chart(self, chat_title):
        self.edit_card(chat_title)
        try:
            self.toggle_chart_wizard_module()
            self.assert_summary_chart_query_filter_default()
            self.assert_summary_chart_query_field_default()

        finally:
            self.click_card_cancel()

    def verify_card_config_reset_comparison_chart(self, chart_title):
        self.edit_card(chart_title)
        try:
            self.toggle_chart_wizard_module()
            self.assert_compression_chart_first_query_field_default()

            self.toggle_chart_wizard_module(selector_element_css=self.COMPARISON_CARD_2ND_CHILD_MODULE_CSS,
                                            ddl_selector_css=self.COMPARISON_CARD_2ND_CHILD_MODULE_CSS,
                                            options_css=self.WIZARD_OPTIONS_CSS)
            self.assert_compression_chart_second_query_field_default()

        finally:
            self.click_card_cancel()

    def verify_card_config_reset_segmentation_chart(self, chart_title):
        self.edit_card(chart_title)
        try:
            self.toggle_chart_wizard_module()
            self.assert_segmentation_chart_query_field_default()
            self.assert_segmentation_chart_field_default()

        finally:
            self.click_card_cancel()

    def fill_card_search_input(self, card, text):
        self.fill_text_field_by_css_selector(self.CARD_SEARCH_INPUT_CSS, text, card)

    def get_card_search_input_text(self, card):
        return card.find_element_by_css_selector(self.CARD_SEARCH_INPUT_CSS).text

    def click_legend_toggle(self, card):
        return card.find_element_by_css_selector(self.TOGGLE_LEGEND_CSS).click()

    def verify_legend_toggle_absent(self, card):
        card_id = card.get_attribute('id')
        self.assert_element_absent_by_css_selector(f'#{card_id} {self.TOGGLE_LEGEND_CSS}')

    def verify_legend_absent(self, card):
        card_id = card.get_attribute('id')
        self.assert_element_absent_by_css_selector(f'#{card_id} {self.CHART_LEGEND_CSS}')

    def get_legend(self, card):
        card.find_elements_by_css_selector(self.CHART_LEGEND_CSS)

    def get_search_insights_tables(self):
        return self.find_elements_by_css(self.TABLE_CONTAINER_CSS)

    def assert_device_explorer_results_exists(self):
        assert self.find_element_by_text('Devices',
                                         self.driver.find_element_by_css_selector(self.EXPLORER_RESULTS_CSS))

    def assert_users_explorer_results_exists(self):
        assert self.find_element_by_text('Users',
                                         self.driver.find_element_by_css_selector(self.EXPLORER_RESULTS_CSS))

    def select_chart_sort(self, card, sort_by, sort_order):
        self.open_close_card_menu(card)
        actions = ActionChains(self.driver)
        actions.move_to_element(self.driver.find_element_by_id(self.CHART_PANEL_SORT_ACTION_ID)).perform()
        actions.move_to_element(self.driver.find_element_by_id(self.CHART_PANEL_SORT_BY_ID.format(
            sort_by=sort_by))).perform()
        actions.click(self.driver.find_element_by_id(
            self.CHART_PANEL_SORT_ORDER_ID.format(sort_by=sort_by, sort_order=sort_order))).perform()
        self.wait_for_card_spinner_to_end()

    def edit_dashboard_chart_default_sort(self, sort_by, sort_order):
        self.driver.find_element_by_css_selector(self.WIZARD_SORT_BY.format(sort_by=sort_by)).click()
        self.driver.find_element_by_css_selector(self.WIZARD_SORT_ORDER.format(sort_order=sort_order)).click()
        self.click_card_save()
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS, interval=1)
        self.wait_for_card_spinner_to_end()

    def has_sort_options(self):
        try:
            self.driver.find_element_by_css_selector(self.WIZARD_SORT_CONTAINER_CSS)
            return True
        except NoSuchElementException:
            # Good, it is missing
            return False
        return True

    @contextmanager
    def edit_and_assert_chart(self, card, assert_data, chart_type=PIE_CHART_TYPE):
        self.open_edit_card(card)
        yield
        self.click_card_save()
        if chart_type == self.PIE_CHART_TYPE:
            self.assert_pie_slices_data(card, assert_data)
        if chart_type == self.HISTOGRAM_CHART_TYPE:
            self.assert_histogram_lines_data(card, assert_data)
        if chart_type == self.SUMMARY_CHART_TYPE:
            self.assert_summary_text_data(card, assert_data)
        if chart_type == self.TIMELINE_CHART_TYPE:
            self.assert_timeline_svg_exist(card)

    def verify_chart_warning_exists(self, card):
        assert card.find_element_by_css_selector(self.CHART_WARNING_CSS)

    def verify_chart_warning_missing(self, card):
        with pytest.raises(NoSuchElementException):
            card.find_element_by_css_selector(self.CHART_WARNING_CSS)

    def get_data_from_timeline_card(self, card):
        self.wait_for_element_present_by_css(self.TIMELINE_CARD_DATA_TABLE_CSS, card)
        table = card.find_element_by_css_selector(self.TIMELINE_CARD_DATA_TABLE_CSS)
        table_rows = table.find_elements_by_tag_name('tr')
        data = {}
        for row in table_rows:
            values = [x.get_attribute('innerText') for x in row.find_elements_by_tag_name('td')]
            date = datetime.datetime.strptime(values[0], '%b %d, %Y, %I:%M:%S %p')
            data[date.strftime('%Y-%m-%d 00:00:00')] = values[1:]
        return data

    def get_pie_chart_slices_total_value(self, pie):
        pie_slices = pie.find_elements_by_css_selector(self.PIE_SLICE_CSS)
        self.hover_over_element(pie_slices[0])
        slice_percentage = self.get_tooltip_body_percentage(pie)
        slice_value = int(self.get_tooltip_body_value(pie))
        return round(100 / (slice_percentage / slice_value))

    def get_pie_chart_footer_total_value(self, pie):
        return int(pie.find_element_by_css_selector(self.PIE_TOTAL_ITEMS_CSS).text.lstrip('Total '))

    def move_to_space_and_assert_title(self, space_index, title):
        self.select_space(space_index)
        assert self.find_space_header_title(space_index) == title
