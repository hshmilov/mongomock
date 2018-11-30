from ui_tests.pages.page import Page


class DashboardPage(Page):
    SHOW_ME_HOW = 'SHOW ME HOW'
    CONGRATULATIONS = 'Congratulations! You are one step closer to'
    MANAGED_DEVICE_COVERAGE = 'Managed Device Coverage'
    SYSTEM_LIFECYCLE = 'System Lifecycle'
    NEW_CHART = 'New Chart'
    DEVICE_DISCOVERY = 'Device Discovery'
    USER_DISCOVERY = 'User Discovery'
    QUERY_SEARCH_INPUT_CSS = 'div:nth-child(1) > div > div > input'
    UNCOVERED_PIE_SLICE_CSS = 'svg > g#managed_coverage_1 > text.scaling'
    COVERED_PIE_SLICE_CSS = 'svg > g#managed_coverage_2 > text.scaling'
    COVERAGE_CARD_CSS = 'div.x-card.coverage'

    @property
    def root_page_css(self):
        return 'li#dashboard.x-nested-nav-item'

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
        return self.driver.find_element_by_css_selector(self.COVERAGE_CARD_CSS)

    def find_system_lifecycle_card(self):
        return self.driver.find_element_by_css_selector('div.x-card.chart-lifecycle.print-exclude')

    def find_new_chart_card(self):
        return self.driver.find_element_by_css_selector('div.x-card.chart-new.print-exclude')

    def find_device_discovery_card(self):
        return self.driver.find_elements_by_css_selector('div.x-card.x-data-discovery-card')[0]

    def find_user_discovery_card(self):
        return self.driver.find_elements_by_css_selector('div.x-card.x-data-discovery-card')[1]

    def fill_query_value(self, text, parent=None):
        self.fill_text_field_by_css_selector(self.QUERY_SEARCH_INPUT_CSS, text, context=parent)

    def enter_search(self):
        self.key_down_enter(self.find_query_search_input())

    def open_view_devices(self):
        self.click_button('View in Devices', partial_class=True, should_scroll_into_view=False)

    def open_view_users(self):
        self.click_button('View in Users', partial_class=True, should_scroll_into_view=False)

    def find_query_search_input(self):
        return self.driver.find_element_by_css_selector(self.QUERY_SEARCH_INPUT_CSS)

    def get_uncovered_from_pie(self, pie):
        return int(pie.find_element_by_css_selector(self.UNCOVERED_PIE_SLICE_CSS).text.rstrip('%'))

    def get_covered_from_pie(self, pie):
        return int(pie.find_element_by_css_selector(self.COVERED_PIE_SLICE_CSS).text.rstrip('%'))

    def click_uncovered_pie_slice(self):
        self.click_managed_device_pie_slice(self.UNCOVERED_PIE_SLICE_CSS)

    def click_covered_pie_slice(self):
        self.click_managed_device_pie_slice(self.COVERED_PIE_SLICE_CSS)

    def click_managed_device_pie_slice(self, slice_css):
        self.wait_for_element_present_by_css(self.COVERAGE_CARD_CSS)
        mdc_card = self.find_managed_device_coverage_card()
        pie = self.get_pie_chart_from_card(mdc_card)
        pie.find_element_by_css_selector(slice_css).click()

    @staticmethod
    def get_title_from_card(card):
        return card.find_element_by_css_selector('div.x-header > div.x-title').text.title()

    @staticmethod
    def get_pie_chart_from_card(card):
        return card.find_element_by_css_selector('div.pie')

    @staticmethod
    def get_cycle_from_card(card):
        return card.find_element_by_css_selector('svg.cycle')

    @staticmethod
    def assert_check_in_cycle(cycle):
        assert cycle.find_element_by_css_selector('path.check')

    @staticmethod
    def assert_cycle_is_stable(cycle):
        assert cycle.find_element_by_css_selector('text.title').text == 'STABLE'

    @staticmethod
    def assert_plus_button_in_card(card):
        assert card.find_element_by_css_selector('div.x-btn.link').text == '+'

    @staticmethod
    def find_adapter_in_card(card, adapter):
        return card.find_element_by_css_selector(f'div[title={adapter}]')

    @staticmethod
    def find_quantity_in_card(card):
        return [int(x.text) for x in card.find_elements_by_css_selector('div.quantity') if x.text]
