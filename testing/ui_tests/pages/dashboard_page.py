from ui_tests.pages.page import Page


class DashboardPage(Page):
    SHOW_ME_HOW = 'SHOW ME HOW'
    CONGRATULATIONS = 'Congratulations! You are one step closer to'
    MANAGED_DEVICE_COVERAGE = 'Managed Device Coverage'
    SYSTEM_LIFECYCLE = 'System Lifecycle'
    NEW_CHART = 'New Chart'
    DEVICE_DISCOVERY = 'Device Discovery'
    USER_DISCOVERY = 'User Discovery'

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
        return self.driver.find_element_by_css_selector('div.x-card.coverage')

    def find_system_lifecycle_card(self):
        return self.driver.find_element_by_css_selector('div.x-card.chart-lifecycle.print-exclude')

    def find_new_chart_card(self):
        return self.driver.find_element_by_css_selector('div.x-card.chart-new.print-exclude')

    def find_device_discovery_card(self):
        return self.driver.find_elements_by_css_selector('div.x-card.x-data-discovery-card')[0]

    def find_user_discovery_card(self):
        return self.driver.find_elements_by_css_selector('div.x-card.x-data-discovery-card')[1]

    @staticmethod
    def get_title_from_card(card):
        return card.find_element_by_css_selector('div.x-header > div.x-title').text.title()

    @staticmethod
    def get_pie_chart_from_card(card):
        return card.find_element_by_css_selector('div.pie')

    @staticmethod
    def get_uncovered_from_pie(pie):
        return int(pie.find_element_by_css_selector('svg > g#managed_coverage_1 > text.scaling').text.rstrip('%'))

    @staticmethod
    def get_covered_from_pie(pie):
        return int(pie.find_element_by_css_selector('svg > g#managed_coverage_2 > text.scaling').text.rstrip('%'))

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
