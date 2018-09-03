import re

from ui_tests.pages.page import Page, BUTTON_TYPE_A


class EntitiesPage(Page):
    QUERY_WIZARD_ID = 'query_wizard'
    QUERY_EXPRESSIONS_CSS = '.filter .expression'
    QUERY_FIELD_DROPDOWN_CSS = '.x-dropdown.x-select.field-select'
    QUERY_ADAPTER_DROPDOWN_CSS = '.x-select-typed-field .x-dropdown.x-select.x-select-symbol'
    QUERY_TEXT_BOX_CSS = 'div.search-input.x-select-search > input'
    QUERY_SELECTED_OPTION_CSS = 'div.x-select-options > div.x-select-option'
    QUERY_SECOND_PHASE_DROPDOWN_CSS = '#query_op > div'
    QUERY_THIRD_PHASE_ID = 'query_value'
    QUERY_SEARCH_INPUT_CSS = '#query_list .input-value'
    QUERY_ADD_EXPRESSION = '.filter .footer .x-btn'
    QUERY_LOGIC_DROPDOWN_CSS = 'div.x-select.x-select-logic'
    TABLE_COUNT_CSS = '.x-table-header .x-title .count'
    TABLE_FIRST_ROW_CSS = 'tbody .x-row.clickable'
    TABLE_FIRST_CELL_CSS = f'{TABLE_FIRST_ROW_CSS} td:nth-child(2)'
    TABLE_DATA_ROWS_XPATH = '//tr[@id]'
    TABLE_PAGE_SIZE_XPATH = '//div[@class=\'x-pagination\']/div[@class=\'x-sizes\']/div[text()=\'{0}\']'
    VALUE_ADAPTERS_JSON = 'JSON File'
    VALUE_ADAPTERS_AD = 'Active Directory'

    @property
    def root_page_css(self):
        raise NotImplementedError

    @property
    def url(self):
        raise NotImplementedError

    def click_query_wizard(self):
        self.driver.find_element_by_id(self.QUERY_WIZARD_ID).click()

    def select_query_field(self, text, parent=None):
        self.select_option(self.QUERY_FIELD_DROPDOWN_CSS,
                           self.QUERY_TEXT_BOX_CSS,
                           self.QUERY_SELECTED_OPTION_CSS,
                           text,
                           parent=parent)

    def select_query_adapter(self, text, parent=None):
        self.select_option(self.QUERY_ADAPTER_DROPDOWN_CSS,
                           self.QUERY_TEXT_BOX_CSS,
                           self.QUERY_SELECTED_OPTION_CSS,
                           text,
                           parent=parent)

    def select_query_second_phase(self, text):
        self.select_option_without_search(self.QUERY_SECOND_PHASE_DROPDOWN_CSS,
                                          self.QUERY_SELECTED_OPTION_CSS,
                                          text)

    def fill_query_third_phase(self, text):
        self.fill_text_field_by_element_id(self.QUERY_THIRD_PHASE_ID, text)

    def select_query_logic_op(self, text):
        self.select_option_without_search(self.QUERY_LOGIC_DROPDOWN_CSS, self.QUERY_SELECTED_OPTION_CSS, text)

    def click_search(self):
        self.click_button('Search', call_space=False, button_type=BUTTON_TYPE_A)

    def find_first_id(self):
        return self.driver.find_element_by_css_selector(self.TABLE_FIRST_ROW_CSS).get_attribute('id')

    def click_row(self):
        self.driver.find_element_by_css_selector(self.TABLE_FIRST_CELL_CSS).click()

    def fill_filter(self, filter_string):
        self.fill_text_field_by_css_selector(self.QUERY_SEARCH_INPUT_CSS, filter_string)

    def enter_search(self):
        self.key_down_enter(self.driver.find_element_by_css_selector(self.QUERY_SEARCH_INPUT_CSS))

    def count_entities(self):
        match_count = re.search(r'\((\d+)\)', self.driver.find_element_by_css_selector(self.TABLE_COUNT_CSS).text)
        assert match_count and len(match_count.groups()) == 1
        return int(match_count.group(1))

    def add_query_expression(self):
        self.driver.find_element_by_css_selector(self.QUERY_ADD_EXPRESSION).click()

    def find_expressions(self):
        return self.driver.find_elements_by_css_selector(self.QUERY_EXPRESSIONS_CSS)

    def find_rows_with_data(self):
        return self.driver.find_elements_by_xpath(self.TABLE_DATA_ROWS_XPATH)

    def select_page_size(self, page_size):
        self.driver.find_element_by_xpath(self.TABLE_PAGE_SIZE_XPATH.format(page_size)).click()
