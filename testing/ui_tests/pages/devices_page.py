from ui_tests.pages.page import Page, BUTTON_TYPE_A


class DevicesPage(Page):
    QUERY_WIZARD_ID = 'query_wizard'
    QUERY_DROPDOWN_CSS = 'div.placeholder'
    QUERY_TEXT_BOX_CSS = 'div.search-input.x-select-search > input'
    QUERY_SELECTED_OPTION_CSS = 'div.x-select-options > div.x-select-option'
    SAVED_QUERY_NETWORK_INTERFACES_IPS = 'Network Interfaces: IPs'
    QUERY_SECOND_PHASE_DROPDOWN_CSS = '#query_op > div'
    QUERY_THIRD_PHASE_ID = 'query_value'

    @property
    def url(self):
        return f'{self.base_url}/devices'

    @property
    def root_page_css(self):
        return 'li#devices.x-nested-nav-item'

    def click_query_wizard(self):
        self.driver.find_element_by_id(self.QUERY_WIZARD_ID).click()

    def select_saved_query(self, text):
        self.select_option(self.QUERY_DROPDOWN_CSS,
                           self.QUERY_TEXT_BOX_CSS,
                           self.QUERY_SELECTED_OPTION_CSS,
                           text)

    def select_query_second_phase(self, text):
        self.select_option_without_search(self.QUERY_SECOND_PHASE_DROPDOWN_CSS,
                                          self.QUERY_SELECTED_OPTION_CSS,
                                          text)

    def fill_query_third_phase(self, text):
        self.fill_text_field_by_element_id(self.QUERY_THIRD_PHASE_ID, text)

    def click_search(self):
        self.click_button('Search', call_space=False, button_type=BUTTON_TYPE_A)
