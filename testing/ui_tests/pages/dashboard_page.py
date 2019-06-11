from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

from ui_tests.pages.page import Page
from services.axon_service import TimeoutException


class DashboardPage(Page):
    SHOW_ME_HOW = 'SHOW ME HOW'
    CONGRATULATIONS = 'Congratulations! You are one step closer to'
    MANAGED_DEVICE_COVERAGE = 'Managed Device Coverage'
    SYSTEM_LIFECYCLE = 'System Lifecycle'
    NEW_CHART = 'New Chart'
    DEVICE_DISCOVERY = 'Device Discovery'
    USER_DISCOVERY = 'User Discovery'
    QUERY_SEARCH_INPUT_CSS = 'div:nth-child(1) > div > div > input'
    UNCOVERED_PIE_SLICE_CSS = 'svg > g#managed_device_coverage_view_0 > text.scaling'
    COVERED_PIE_SLICE_CSS = 'svg > g#managed_device_coverage_view_1 > text.scaling'
    INTERSECTION_PIE_INTERSECTION_SLICE_CSS = '{id} > div.x-pie > svg > g:nth-child(4) > text'
    SYMMETRIC_DIFFERENCE_FROM_BASE_QUERY_SLICE_CSS = '{id} > div.x-pie > svg > g:nth-child(2)'
    SYMMETRIC_DIFFERENCE_FROM_FIRST_QUERY_SLICE_CSS = '{id} > div.x-pie > svg > g:nth-child(3)'
    SYMMETRIC_DIFFERENCE_FROM_SECOND_QUERY_SLICE_CSS = '{id} > div.x-pie > svg > g:nth-child(1)'
    NEW_CARD_WIZARD_CSS = '.x-tab.active .x-card.chart-new'
    CHART_METRIC_DROP_DOWN_CSS = '#metric > div'
    INTERSECTION_CHART_FIRST_QUERY_DROP_DOWN_CSS = '#intersectingFirst > div'
    INTERSECTION_CHART_SECOND_QUERY_DROP_DOWN_CSS = '#intersectingSecond > div'
    WIZARD_OPTIONS_CSS = 'div.x-select-options > div.x-select-option'
    CHART_MODULE_DROP_DOWN_CSS = 'div.x-chart-metric.grid-span2 > div.x-dropdown.x-select.x-select-symbol'
    CHART_FIELD_DROP_DOWN_CSS = '.x-dropdown.x-select.field-select'
    CHART_FIELD_TEXT_BOX_CSS = 'div.x-search-input.x-select-search > input'
    CHART_FUNCTION_CSS = 'div.x-chart-metric.grid-span2 > div:nth-child(8)'
    CHART_TITLE_ID = 'chart_name'
    SUMMARY_CARD_TEXT_CSS = '{id} > div.x-summary > div.summary'
    CARD_CLOSE_BTN_CSS = '{id} > div.header > button.remove'
    BANNER_BY_TEXT_XPATH = '//div[contains(@class, \'x-banner\') and .//text() = \'{banner_text}\']'

    SPACES_XPATH = '//div[@class=\'x-spaces\']'
    ACTIVE_SPACE_HEADERS_XPATH = f'{SPACES_XPATH}//li[@class=\'header-tab active\']'
    SPACE_HEADERS_XPATH = f'{SPACES_XPATH}//li[contains(@class, \'header-tab\')]'
    SPACE_HEADER_CSS = '.x-spaces .x-tabs .header-tab:nth-child({tab_index})'
    NEW_SPACE_BUTTON_XPATH = f'{SPACES_XPATH}//li[@class=\'add-tab\']'

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
        return self.driver.find_element_by_id(self.get_card_id_from_title(self.MANAGED_DEVICE_COVERAGE))

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
        self.wait_for_element_present_by_css(self.NEW_CARD_WIZARD_CSS).click()

    def select_chart_metric(self, option):
        self.wait_for_element_present_by_css(self.CHART_METRIC_DROP_DOWN_CSS)
        self.select_option_without_search(self.CHART_METRIC_DROP_DOWN_CSS, self.WIZARD_OPTIONS_CSS, option, parent=None)

    def select_intersection_chart_first_query(self, query):
        self.select_option_without_search(self.INTERSECTION_CHART_FIRST_QUERY_DROP_DOWN_CSS,
                                          self.WIZARD_OPTIONS_CSS, query, parent=None)

    def select_intersection_chart_second_query(self, query):
        self.select_option_without_search(self.INTERSECTION_CHART_SECOND_QUERY_DROP_DOWN_CSS,
                                          self.WIZARD_OPTIONS_CSS, query, parent=None)

    def select_chart_wizard_module(self, entity):
        self.select_option_without_search(self.CHART_MODULE_DROP_DOWN_CSS, self.WIZARD_OPTIONS_CSS,
                                          entity, parent=None)

    def select_chart_wizard_field(self, prop):
        self.select_option(self.CHART_FIELD_DROP_DOWN_CSS,
                           self.CHART_FIELD_TEXT_BOX_CSS,
                           self.WIZARD_OPTIONS_CSS, prop, parent=None)

    def select_chart_summary_function(self, func_name):
        self.select_option_without_search(self.CHART_FUNCTION_CSS, self.WIZARD_OPTIONS_CSS, func_name, parent=None)

    def add_intersection_card(self, module, first_query, second_query, title):
        self.open_new_card_wizard()
        self.select_chart_metric('Query Intersection')
        self.select_chart_wizard_module(module)
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

    def add_segmentation_card(self, module, field, title, chart_type='histogram'):
        try:
            self.open_new_card_wizard()
            self.select_chart_metric('Field Segmentation')
            self.driver.find_element_by_css_selector(f'#{chart_type}').click()
            self.select_chart_wizard_module(module)
            self.select_chart_wizard_field(field)
            self.fill_text_field_by_element_id(self.CHART_TITLE_ID, title)
            self.click_button('Save')
            self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS, interval=1)
        except NoSuchElementException:
            # in case of wrong field input return false and change it in order to continue the test
            el = self.driver.find_element_by_css_selector(self.CHART_FIELD_TEXT_BOX_CSS)
            self.fill_text_by_element(el, 'OS: Type')
            self.driver.find_element_by_css_selector(self.WIZARD_OPTIONS_CSS).click()
            self.click_button('Cancel', partial_class=True)
            return False
        return True

    def get_summary_card_text(self, card_title):
        card_id_css = self.get_card_id_css_from_title(card_title)
        return self.wait_for_element_present_by_css(self.SUMMARY_CARD_TEXT_CSS.format(id=card_id_css))

    def get_card(self, card_title):
        card_id_css = self.get_card_id_css_from_title(card_title)
        return self.wait_for_element_present_by_css(card_id_css)

    def get_all_cards(self):
        return self.driver.find_elements_by_css_selector('div.x-card')

    def click_segmentation_pie_card(self, card_title):
        card = self.get_card(card_title)
        pie = self.get_pie_chart_from_card(card)
        pie.find_element_by_css_selector('svg').click()

    def remove_card(self, card_title):
        card_close_button_css = self.CARD_CLOSE_BTN_CSS.format(id=self.get_card_id_css_from_title(card_title))
        self.driver.find_element_by_css_selector(card_close_button_css).click()
        self.wait_for_element_absent_by_css(card_close_button_css)

    def find_query_search_input(self):
        return self.driver.find_element_by_css_selector(self.QUERY_SEARCH_INPUT_CSS)

    def get_uncovered_from_pie(self, pie):
        return int(pie.find_element_by_css_selector(self.UNCOVERED_PIE_SLICE_CSS).text.rstrip('%'))

    def get_covered_from_pie(self, pie):
        return int(pie.find_element_by_css_selector(self.COVERED_PIE_SLICE_CSS).text.rstrip('%'))

    def click_uncovered_pie_slice(self):
        card_id = self.get_card_id_from_title(self.MANAGED_DEVICE_COVERAGE)
        self.click_pie_slice(self.UNCOVERED_PIE_SLICE_CSS, card_id)

    def click_covered_pie_slice(self):
        card_id = self.get_card_id_from_title(self.MANAGED_DEVICE_COVERAGE)
        self.click_pie_slice(self.COVERED_PIE_SLICE_CSS, card_id)

    def click_intersection_pie_slice(self, card_title):
        card_id = self.get_card_id_from_title(card_title)
        card_id_css = self.get_card_id_css_from_title(card_title)
        self.click_pie_slice(self.INTERSECTION_PIE_INTERSECTION_SLICE_CSS.format(id=card_id_css), card_id)

    def click_symmetric_difference_base_query_pie_slice(self, card_title):
        card_id = self.get_card_id_from_title(card_title)
        card_id_css = self.get_card_id_css_from_title(card_title)
        self.click_pie_slice(self.SYMMETRIC_DIFFERENCE_FROM_BASE_QUERY_SLICE_CSS.format(id=card_id_css), card_id)

    def click_symmetric_difference_first_query_pie_slice(self, card_title):
        card_id = self.get_card_id_from_title(card_title)
        card_id_css = self.get_card_id_css_from_title(card_title)
        self.click_pie_slice(self.SYMMETRIC_DIFFERENCE_FROM_FIRST_QUERY_SLICE_CSS.format(id=card_id_css), card_id)

    def click_pie_slice(self, slice_css, card_id):
        self.wait_for_element_present_by_id(card_id)
        card = self.driver.find_element_by_id(card_id)
        pie = self.get_pie_chart_from_card(card)
        pie.find_element_by_css_selector(slice_css).click()

    @staticmethod
    def get_title_from_card(card):
        return card.find_element_by_css_selector('div.header > div.title').text.title()

    @staticmethod
    def get_card_id_from_title(card_title):
        id_string = '_'.join(card_title.lower().split(' '))
        return id_string

    @staticmethod
    def get_card_id_css_from_title(card_title):
        id_string = '_'.join(card_title.split(' ')).lower()
        return f'#{id_string}'

    @staticmethod
    def get_pie_chart_from_card(card):
        return card.find_element_by_css_selector('div.x-pie')

    @staticmethod
    def get_histogram_chart_from_card(card):
        return card.find_element_by_css_selector('div.x-histogram')

    @staticmethod
    def get_histogram_line_from_histogram(histogram, number):
        return histogram.find_element_by_css_selector(f'div:nth-child({number}) > div.item-bar div.quantity')

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

    def add_new_space(self, space_name):
        self.find_add_space().click()
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
        ActionChains(self.driver).move_to_element(space_header).perform()
        space_header.find_element_by_css_selector('.x-button.link').click()
        self.wait_for_element_absent_by_css(self.SPACE_HEADER_CSS.format(tab_index=index))

    def is_missing_space(self, space_name):
        try:
            self.find_element_by_text(space_name)
        except NoSuchElementException:
            # Good, we want it gone
            return True
        return False

    def is_missing_panel(self, panel_name):
        try:
            self.driver.find_element_by_css_selector(f'.x-tab.active {self.get_card_id_css_from_title(panel_name)}')
        except NoSuchElementException:
            # Good, it is missing
            return True
        return False
