import time
import datetime

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

from ui_tests.pages.page import Page, TAB_BODY
from services.axon_service import TimeoutException
from axonius.utils.wait import wait_until


class DashboardPage(Page):
    SHOW_ME_HOW = 'SHOW ME HOW'
    CONGRATULATIONS = 'Congratulations! You are one step closer to'
    MANAGED_DEVICE_COVERAGE = 'Managed Device Coverage'
    SYSTEM_LIFECYCLE = 'System Lifecycle'
    NEW_CHART = 'New Chart'
    DEVICE_DISCOVERY = 'Device Discovery'
    USER_DISCOVERY = 'User Discovery'
    QUERY_SEARCH_INPUT_CSS = 'div:nth-child(1) > div > div > input'
    UNCOVERED_PIE_SLICE_CSS = 'svg > g.slice-0 > text.scaling'
    COVERED_PIE_SLICE_CSS = 'svg > g.slice-1 > text.scaling'
    INTERSECTION_PIE_INTERSECTION_SLICE_CSS = 'svg > g.slice-2 > text'
    SYMMETRIC_DIFFERENCE_FROM_BASE_QUERY_SLICE_CSS = 'svg > g.slice-0 > text'
    SYMMETRIC_DIFFERENCE_FROM_FIRST_QUERY_SLICE_CSS = 'svg > g.slice-1 > text'
    SYMMETRIC_DIFFERENCE_FROM_SECOND_QUERY_SLICE_CSS = 'svg > g.slice-3 > text'
    NEW_CARD_WIZARD_CSS = '.x-tab.active .x-card.chart-new'
    CHART_METRIC_DROP_DOWN_CSS = '#metric > div'
    INTERSECTION_CHART_FIRST_QUERY_DROP_DOWN_CSS = '#intersectingFirst > div'
    INTERSECTION_CHART_SECOND_QUERY_DROP_DOWN_CSS = '#intersectingSecond > div'
    WIZARD_OPTIONS_CSS = 'div.x-select-options > div.x-select-option'
    CHART_WIZARD_CSS = '.x-chart-wizard'
    CHART_MODULE_DROP_DOWN_CSS = '.x-chart-wizard .x-select.x-select-symbol'
    SELECT_VIEWS_CSS = '.x-select-views'
    SELECT_VIEWS_VIEW_CSS = '.view'
    SELECT_VIEW_NAME_CSS = '.view-name'
    CHART_FIELD_DROP_DOWN_CSS = '.x-dropdown.x-select.field-select'
    CHART_FIELD_TEXT_BOX_CSS = 'div.x-search-input.x-select-search > input'
    CHART_FUNCTION_CSS = 'div.x-chart-metric.grid-span2 > div:nth-child(8)'
    CHART_TITLE_ID = 'chart_name'
    SUMMARY_CARD_TEXT_CSS = 'div.x-summary > div.summary'
    CARD_CLOSE_BTN_CSS = '.actions > .remove'
    CARD_EDIT_BTN_CSS = '.actions > .edit'
    CARD_EXPORT_TO_CSV_BTN_CSS = '.actions > .export'
    BANNER_BY_TEXT_XPATH = '//div[contains(@class, \'x-banner\') and .//text() = \'{banner_text}\']'

    SPACES_XPATH = '//div[@class=\'x-spaces\']'
    ACTIVE_SPACE_HEADERS_XPATH = f'{SPACES_XPATH}//li[@class=\'header-tab active\']'
    SPACE_HEADERS_XPATH = f'{SPACES_XPATH}//li[contains(@class, \'header-tab\')]'
    SPACE_HEADER_CSS = '.x-spaces .x-tabs .header-tab:nth-child({tab_index})'
    NEW_SPACE_BUTTON_XPATH = f'{SPACES_XPATH}//li[@class=\'add-tab\']'
    PANEL_BY_NAME_XPATH = '//div[contains(@class, \'x-tab active\')]//div[@class=\'x-card\' ' \
                          'and .//text()=\'{panel_name}\']'
    NO_DATA_FOUND_TEXT = 'No data found'
    PAGINATOR_CLASS = '.x-paginator'
    PAGINATOR_LIMIT = '.num-of-items'
    PAGINATOR_TO = ' .to-item'
    PAGINATOR_BUTTON = f'{PAGINATOR_CLASS} .x-button'
    PAGINATOR_FIRST_PAGE_BUTTON = f'{PAGINATOR_BUTTON}.link.first'
    PAGINATOR_PREVIOUS_PAGE_BUTTON = f'{PAGINATOR_BUTTON}.link.previous'
    PAGINATOR_NEXT_PAGE_BUTTON = f'{PAGINATOR_BUTTON}.link.next'
    PAGINATOR_LAST_PAGE_BUTTON = f'{PAGINATOR_BUTTON}.link.last'
    PAGINATOR_TEXT = f'{PAGINATOR_CLASS} .pagintator-text'
    HISTOGRAM_ITEMS = '.histogram-container .histogram-item'
    PAGINATOR_NUM_OF_ITEMS = f'{PAGINATOR_CLASS} {PAGINATOR_LIMIT}'
    PAGINATOR_TOTAL_NUM_OF_ITEMS = f'{PAGINATOR_CLASS} .total-num-of-items'
    PAGINATOR_FROM_VALUE = f'{PAGINATOR_CLASS} .from-item'
    PAGINATOR_TO_VALUE = f'{PAGINATOR_CLASS} {PAGINATOR_TO}'

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
        assert self.find_element_by_text(self.CONGRATULATIONS).text == \
            f'{self.CONGRATULATIONS}\nhaving all your assets visible in one place.'

    def find_managed_device_coverage_card(self):
        return self.driver.find_element_by_xpath(
            self.PANEL_BY_NAME_XPATH.format(panel_name=self.MANAGED_DEVICE_COVERAGE))

    def find_system_lifecycle_card(self):
        return self.driver.find_element_by_css_selector('div.x-card.chart-lifecycle.print-exclude')

    def find_new_chart_card(self):
        return self.driver.find_element_by_css_selector('.x-tab.active div.x-card.chart-new.print-exclude')

    def find_device_discovery_card(self):
        return self.driver.find_elements_by_css_selector('div.x-card.x-discovery-card')[0]

    def find_user_discovery_card(self):
        return self.driver.find_elements_by_css_selector('div.x-card.x-discovery-card')[1]

    def fill_query_value(self, text, parent=None):
        self.fill_text_field_by_css_selector(self.QUERY_SEARCH_INPUT_CSS, text, context=parent)

    def enter_search(self):
        self.key_down_enter(self.find_query_search_input())

    def open_view_devices(self):
        self.click_button('View in Devices', partial_class=True, should_scroll_into_view=False)

    def open_view_users(self):
        self.click_button('View in Users', partial_class=True, should_scroll_into_view=False)

    def open_new_card_wizard(self):
        new_card = self.wait_for_element_present_by_css(self.NEW_CARD_WIZARD_CSS)
        self.scroll_into_view(new_card, window=TAB_BODY)
        new_card.click()

    def select_chart_metric(self, option):
        self.wait_for_element_present_by_css(self.CHART_METRIC_DROP_DOWN_CSS)
        self.select_option_without_search(self.CHART_METRIC_DROP_DOWN_CSS, self.WIZARD_OPTIONS_CSS, option, parent=None)

    def select_chart_view_name(self, view_name, parent=None):
        self.select_option(self.SELECT_VIEW_NAME_CSS,
                           self.DROPDOWN_TEXT_BOX_CSS,
                           self.DROPDOWN_SELECTED_OPTION_CSS,
                           view_name,
                           parent=parent)

    def select_intersection_chart_first_query(self, query):
        self.select_option_without_search(self.INTERSECTION_CHART_FIRST_QUERY_DROP_DOWN_CSS,
                                          self.WIZARD_OPTIONS_CSS, query, parent=None)

    def select_intersection_chart_second_query(self, query):
        self.select_option_without_search(self.INTERSECTION_CHART_SECOND_QUERY_DROP_DOWN_CSS,
                                          self.WIZARD_OPTIONS_CSS, query, parent=None)

    def select_chart_wizard_module(self, entity, parent=None):
        self.select_option_without_search(self.CHART_MODULE_DROP_DOWN_CSS, self.WIZARD_OPTIONS_CSS,
                                          entity, parent=parent)

    def select_chart_wizard_field(self, prop, partial_text=True):
        self.select_option(self.CHART_FIELD_DROP_DOWN_CSS,
                           self.CHART_FIELD_TEXT_BOX_CSS,
                           self.WIZARD_OPTIONS_CSS, prop,
                           parent=None,
                           partial_text=partial_text)

    def select_chart_summary_function(self, func_name):
        self.select_option_without_search(self.CHART_FUNCTION_CSS, self.WIZARD_OPTIONS_CSS, func_name, parent=None)

    def get_views_list(self):
        return self.wait_for_element_present_by_css(self.SELECT_VIEWS_CSS).find_elements_by_css_selector(
            self.SELECT_VIEWS_VIEW_CSS)

    def add_comparison_card(self, first_module, first_query, second_module, second_query,
                            title, chart_type='histogram'):
        self.open_new_card_wizard()
        self.select_chart_metric('Query Comparison')
        views_list = self.get_views_list()
        self.driver.find_element_by_css_selector(f'#{chart_type}').click()
        self.select_chart_wizard_module(first_module, views_list[0])
        self.select_chart_view_name(first_query, views_list[0])
        self.select_chart_wizard_module(second_module, views_list[1])
        self.select_chart_view_name(second_query, views_list[1])
        self.fill_text_field_by_element_id(self.CHART_TITLE_ID, title)
        self.click_button('Save')
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS, interval=1)

    def add_comparison_card_view(self, module, query):
        self.click_button('+', partial_class=True,
                          context=self.driver.find_element_by_css_selector(self.CHART_WIZARD_CSS))
        views_list = self.get_views_list()
        self.select_chart_wizard_module(module, views_list[2])
        self.select_chart_view_name(query, views_list[2])
        self.click_button('Save')
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS, interval=1)

    def add_intersection_card(self, module, first_query, second_query, title, view_name=''):
        self.open_new_card_wizard()
        self.select_chart_metric('Query Intersection')
        self.select_chart_wizard_module(module)
        if view_name:
            self.select_chart_view_name(view_name)
        self.select_intersection_chart_first_query(first_query)
        self.select_intersection_chart_second_query(second_query)
        self.fill_text_field_by_element_id(self.CHART_TITLE_ID, title)
        self.click_button('Save')
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS, interval=1)

    def add_summary_card(self, module, field, func_name, title):
        self.open_new_card_wizard()
        self.select_chart_metric('Field Summary')
        self.select_chart_wizard_module(module)
        self.select_chart_wizard_field(field)
        self.select_chart_summary_function(func_name)
        self.fill_text_field_by_element_id(self.CHART_TITLE_ID, title)
        self.click_button('Save')
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS, interval=1)

    def add_segmentation_card(self, module, field, title, chart_type='histogram', view_name='', partial_text=True):
        try:
            self.open_new_card_wizard()
            self.select_chart_metric('Field Segmentation')
            self.driver.find_element_by_css_selector(f'#{chart_type}').click()
            self.select_chart_wizard_module(module)
            if view_name:
                self.select_chart_view_name(view_name)
            self.select_chart_wizard_field(field, partial_text)
            self.fill_text_field_by_element_id(self.CHART_TITLE_ID, title)
            self.click_button('Save')
            self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS, interval=1)
        except NoSuchElementException:
            self.close_dropdown()
            self.click_button('Cancel', partial_class=True)
            self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS)
            return False
        return True

    def get_summary_card_text(self, card_title):
        return self.wait_for_element_present_by_css(self.SUMMARY_CARD_TEXT_CSS,
                                                    element=self.driver.find_element_by_xpath(
                                                        self.PANEL_BY_NAME_XPATH.format(panel_name=card_title)))

    def get_card(self, card_title):
        return self.wait_for_element_present_by_xpath(self.PANEL_BY_NAME_XPATH.format(panel_name=card_title))

    def get_all_cards(self):
        return self.driver.find_elements_by_css_selector('.x-tab.active div.x-card')

    def click_segmentation_pie_card(self, card_title):
        card = self.get_card(card_title)
        pie = self.get_pie_chart_from_card(card)
        pie.find_element_by_css_selector('svg').click()

    def edit_card(self, card_title):
        card = self.get_card(card_title)
        ActionChains(self.driver).move_to_element(card).perform()
        card.find_element_by_css_selector(self.CARD_EDIT_BTN_CSS).click()
        self.wait_for_element_present_by_css(self.MODAL_OVERLAY_CSS)

    def remove_card(self, card_title):
        panel = self.wait_for_element_present_by_xpath(self.PANEL_BY_NAME_XPATH.format(panel_name=card_title))
        self.scroll_into_view(panel, window=TAB_BODY)
        ActionChains(self.driver).move_to_element(panel).perform()
        panel.find_element_by_css_selector(self.CARD_CLOSE_BTN_CSS).click()
        self.wait_for_element_present_by_css(self.MODAL_OVERLAY_CSS)
        self.click_button('Remove Chart')
        wait_until(lambda: self.is_missing_panel(card_title))

    def export_card(self, card_title):
        card = self.get_card(card_title)
        ActionChains(self.driver).move_to_element(card).perform()
        card.find_element_by_css_selector(self.CARD_EXPORT_TO_CSV_BTN_CSS).click()

    def find_query_search_input(self):
        return self.driver.find_element_by_css_selector(self.QUERY_SEARCH_INPUT_CSS)

    def get_uncovered_from_pie(self, pie):
        return int(pie.find_element_by_css_selector(self.UNCOVERED_PIE_SLICE_CSS).text.rstrip('%'))

    def get_covered_from_pie(self, pie):
        return int(pie.find_element_by_css_selector(self.COVERED_PIE_SLICE_CSS).text.rstrip('%'))

    def click_uncovered_pie_slice(self):
        self.click_pie_slice(self.UNCOVERED_PIE_SLICE_CSS, self.MANAGED_DEVICE_COVERAGE)

    def click_covered_pie_slice(self):
        self.click_pie_slice(self.COVERED_PIE_SLICE_CSS, self.MANAGED_DEVICE_COVERAGE)

    def click_intersection_pie_slice(self, card_title):
        self.click_pie_slice(self.INTERSECTION_PIE_INTERSECTION_SLICE_CSS, card_title)

    def click_symmetric_difference_base_query_pie_slice(self, card_title):
        self.click_pie_slice(self.SYMMETRIC_DIFFERENCE_FROM_BASE_QUERY_SLICE_CSS, card_title)

    def click_symmetric_difference_first_query_pie_slice(self, card_title):
        self.click_pie_slice(self.SYMMETRIC_DIFFERENCE_FROM_FIRST_QUERY_SLICE_CSS, card_title)

    def click_pie_slice(self, slice_css, card_title):
        card = self.wait_for_element_present_by_xpath(self.PANEL_BY_NAME_XPATH.format(panel_name=card_title))
        time.sleep(2)
        card_slice = self.get_pie_chart_from_card(card).find_element_by_css_selector(slice_css)
        self.scroll_into_view(card_slice, window=TAB_BODY)
        card_slice.click()

    @staticmethod
    def get_title_from_card(card):
        return card.find_element_by_css_selector('div.header > div.title').text.title()

    @staticmethod
    def get_pie_chart_from_card(card):
        return card.find_element_by_css_selector('div.x-pie')

    @staticmethod
    def get_histogram_chart_from_card(card):
        return card.find_element_by_css_selector('.x-histogram')

    @staticmethod
    def get_histogram_line_from_histogram(histogram, number):
        return histogram.find_element_by_css_selector(f'div:nth-child({number}) > .item-bar div.quantity')

    def get_count_histogram_lines_from_histogram(self, histogram):
        return len(histogram.find_elements_by_css_selector(self.HISTOGRAM_ITEMS))

    def get_histogram_items_on_pagination(self, histogram):
        return histogram.find_elements_by_css_selector(self.HISTOGRAM_ITEMS)

    def get_histogram_items_title_on_pagination(self, histogram):
        histogram_items_title = []
        histogram_items = self.get_histogram_items_on_pagination(histogram)
        for line_item in histogram_items:
            histogram_items_title.append(line_item.find_element_by_css_selector('.item-bar~div[title]').text)
        return histogram_items_title

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
    def calculate_from_item_value(total_num_of_items, num_of_items, num_of_pages, curr_page, to_val, limit):
        if num_of_items % limit != 0 and curr_page == num_of_pages:
            return num_of_items - (num_of_items % limit) + 1
        return to_val - limit + 1

    @staticmethod
    def calculate_to_item_value(total_num_of_items, num_of_items, page_number, limit):
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

    def check_paginator_buttons_state(self, histogram, first, previous, next_r, last):
        paginator_current_buttons_state = [
            self.has_class(self.get_first_page_button_in_paginator(histogram), 'disabled'),
            self.has_class(self.get_previous_page_button_in_paginator(histogram), 'disabled'),
            self.has_class(self.get_next_page_button_in_paginator(histogram), 'disabled'),
            self.has_class(self.get_last_page_button_in_paginator(histogram), 'disabled')
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
        assert cycle.find_element_by_css_selector('text.title').text == 'STABLE'

    @staticmethod
    def assert_cycle_start_and_finish_dates(card):
        dates = card.find_elements_by_css_selector('.cycle-date')
        date_start = datetime.datetime.strptime(dates[0].text, '%Y-%m-%d %H:%M:%S')
        date_finish = datetime.datetime.strptime(dates[1].text, '%Y-%m-%d %H:%M:%S')
        assert date_finish > date_start

    @staticmethod
    def assert_plus_button_in_card(card):
        assert card.find_element_by_css_selector('.x-button.link').text == '+'

    @staticmethod
    def assert_plus_button_disabled_in_card(card):
        assert card.find_element_by_css_selector('.x-button.link.disabled').text == '+'

    @staticmethod
    def find_adapter_in_card(card, adapter):
        return card.find_element_by_css_selector(f'div[title={adapter}]')

    @staticmethod
    def find_quantity_in_card(card):
        return [int(x.text) for x in card.find_elements_by_css_selector('div.quantity') if x.text]

    def find_no_trial_banner(self):
        self.wait_for_element_absent_by_css('.x-trial-banner')

    def find_trial_remainder_banner(self, remainder_count):
        msg = 'days remaining in your Axonius evaluation'
        # Expected color of the banner according UIs thresholds
        color = '208, 1, 27' if (remainder_count <= 7) else (
            '246, 166, 35' if remainder_count <= 14 else '71, 150, 228')
        try:
            banner = self.wait_for_element_present_by_xpath(
                self.BANNER_BY_TEXT_XPATH.format(banner_text=f'{remainder_count} {msg}'))
        except TimeoutException:
            # Currently there is a bug, probably if it is running in midnight AX-3730
            banner = self.wait_for_element_present_by_xpath(
                self.BANNER_BY_TEXT_XPATH.format(banner_text=f'{remainder_count + 1} {msg}'))
        assert banner.value_of_css_property('background-color') == f'rgba({color}, 1)'
        return banner

    def find_trial_expired_banner(self):
        return self.wait_for_element_present_by_text(
            'Axonius evaluation period has expired. Please reach out to your Account Manager.')

    def find_active_space_header_title(self):
        return self.driver.find_element_by_xpath(self.ACTIVE_SPACE_HEADERS_XPATH).text

    def find_space_header(self, index=1):
        return self.find_elements_by_xpath(self.SPACE_HEADERS_XPATH)[index - 1]

    def find_space_header_title(self, index=1):
        return self.find_space_header(index).find_element_by_tag_name('div').text

    def save_space_name(self, space_name):
        name_input = self.wait_for_element_present_by_id(self.RENAME_TAB_INPUT_ID)
        self.fill_text_by_element(name_input, space_name)
        self.click_button(self.OK_BUTTON)
        self.wait_for_modal_close()

    def find_add_space(self):
        return self.driver.find_element_by_xpath(self.NEW_SPACE_BUTTON_XPATH)

    def wait_add_space(self):
        return self.wait_for_element_present_by_xpath(self.NEW_SPACE_BUTTON_XPATH)

    def add_new_space(self, space_name):
        self.wait_add_space().click()
        self.save_space_name(space_name)

    def is_missing_add_space(self):
        try:
            self.find_add_space()
        except NoSuchElementException:
            # Good, indeed missing
            return True
        return False

    def rename_space(self, space_name, index=2):
        # Default 2 since 1 is not renamable
        ActionChains(self.driver).double_click(self.find_space_header(index)).perform()
        self.save_space_name(space_name)

    def remove_space(self, index=3):
        # Default 3 since 1 and 2 are note removable
        space_header = self.find_space_header(index)
        space_header_text = space_header.text
        ActionChains(self.driver).move_to_element(space_header).perform()
        space_header.find_element_by_css_selector('.x-button.link').click()
        self.wait_for_element_present_by_css(self.MODAL_OVERLAY_CSS)
        self.click_button('Remove Space')
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
        return self.find_element_by_text(self.NO_DATA_FOUND_TEXT)
