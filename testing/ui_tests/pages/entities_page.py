import re

from retrying import retry

from ui_tests.pages.page import Page


class EntitiesPage(Page):
    QUERY_WIZARD_ID = 'query_wizard'
    QUERY_EXPRESSIONS_CSS = '.filter .expression'
    QUERY_FIELD_DROPDOWN_CSS = '.x-dropdown.x-select.field-select'
    QUERY_ADAPTER_DROPDOWN_CSS = '.x-select-typed-field .x-dropdown.x-select.x-select-symbol'
    QUERY_TEXT_BOX_CSS = 'div.search-input.x-select-search > input'
    QUERY_SELECTED_OPTION_CSS = 'div.x-select-options > div.x-select-option'
    QUERY_COMP_OP_DROPDOWN_CSS = 'div.x-select.x-select-comp'
    QUERY_VALUE_COMPONENT_CSS = '.expression-value'
    QUERY_SEARCH_INPUT_CSS = '#query_list .input-value'
    QUERY_SEARCH_DROPDOWN_XPATH = '//div[@id=\'query_select\']//div[text()=\'{query_name_text}\']'
    QUERY_SEARCH_EVERYWHERE_XPATH = '//div[@class=\'query-quick\']//div[contains(text(), \'Search in table:\')]'
    QUERY_ADD_EXPRESSION_CSS = '.filter .footer .x-btn'
    QUERY_BRACKET_LEFT_CSS = '.expression-bracket-left'
    QUERY_BRACKET_RIGHT_CSS = '.expression-bracket-right'
    QUERY_NOT_CSS = '.expression-not'
    QUERY_REMOVE_EXPRESSION_CSS = '.x-btn.expression-remove'
    QUERY_LOGIC_DROPDOWN_CSS = 'div.x-select.x-select-logic'
    QUERY_ERROR_CSS = '.filter .error-text'
    QUERY_COMP_EXISTS = 'exists'
    QUERY_COMP_CONTAINS = 'contains'
    QUERY_COMP_EQUALS = 'equals'
    QUERY_COMP_SUBNET = 'subnet'
    QUERY_COMP_SIZE = 'size'
    QUERY_LOGIC_AND = 'and'
    QUERY_LOGIC_OR = 'or'
    TABLE_COUNT_CSS = '.x-table-header .x-title .count'
    TABLE_FIRST_ROW_CSS = 'tbody .x-row.clickable'
    TABLE_FIRST_CELL_CSS = f'{TABLE_FIRST_ROW_CSS} td:nth-child(2)'
    TABLE_FIRST_ROW_CHECKBOX_CSS = f'{TABLE_FIRST_ROW_CSS} td:nth-child(1) .x-checkbox'
    TABLE_FIRST_ROW_TAG_CSS = f'{TABLE_FIRST_ROW_CSS} td:last-child'
    TABLE_DATA_ROWS_XPATH = '//tr[@id]'
    TABLE_PAGE_SIZE_XPATH = '//div[@class=\'x-pagination\']/div[@class=\'x-sizes\']/div[text()=\'{page_size_text}\']'
    VALUE_ADAPTERS_JSON = 'JSON File'
    VALUE_ADAPTERS_AD = 'Active Directory'
    TABLE_HEADER_CELLS_CSS = 'th'
    TABLE_HEADER_SORT_XPATH = '//th[contains(@class, \'sortable\') and contains(text(), \'{col_name_text}\')]'
    TABLE_DATA_POS_XPATH = '//tr[@id]/td[position()={data_position}]'
    TABLE_COLUMNS_MENU_CSS = '.x-field-menu-filter'
    TABLE_ACTIONS_TAG_CSS = 'div.content.w-sm > div > div:nth-child(1) > div.item-content'
    SAVE_QUERY_ID = 'query_save'
    SAVE_QUERY_NAME_ID = 'saveName'
    SAVE_QUERY_SAVE_BUTTON_ID = 'query_save_confirm'
    ALL_COLUMN_NAMES_CSS = 'thead>tr>th'
    ALL_ENTITIES_CSS = 'tbody>tr'
    JSON_ADAPTER_FILTER = 'adapters == "json_file_adapter"'
    DATEPICKER_INPUT_CSS = '.md-datepicker .md-input'
    DATEPICKER_CLEAR_CSS = '.md-datepicker .md-button'
    DATEPICKER_OVERLAY_CSS = '.md-datepicker-overlay'
    NOTES_TAB_CSS = 'li#notes'
    NOTES_CREATED_TOASTER = 'New note was created'
    NOTES_EDITED_TOASTER = 'Existing note was edited'
    NOTES_REMOVED_TOASTER = 'Notes were removed'

    @property
    def url(self):
        raise NotImplementedError

    @property
    def root_page_css(self):
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

    def select_query_comp_op(self, text, parent=None):
        self.select_option_without_search(self.QUERY_COMP_OP_DROPDOWN_CSS,
                                          self.QUERY_SELECTED_OPTION_CSS,
                                          text,
                                          parent=parent)

    def fill_query_value(self, text, parent=None):
        self.fill_text_field_by_css_selector(self.QUERY_VALUE_COMPONENT_CSS, text, context=parent)

    def select_query_value(self, text, parent=None):
        self.select_option(self.QUERY_VALUE_COMPONENT_CSS,
                           self.QUERY_TEXT_BOX_CSS,
                           self.QUERY_SELECTED_OPTION_CSS,
                           text, parent=parent)

    def get_query_value(self):
        el = self.wait_for_element_present_by_css(self.QUERY_VALUE_COMPONENT_CSS)
        return el.get_attribute('value')

    def select_query_logic_op(self, text, parent=None):
        self.select_option_without_search(self.QUERY_LOGIC_DROPDOWN_CSS, self.QUERY_SELECTED_OPTION_CSS, text,
                                          parent=parent)

    def click_search(self):
        self.click_button('Search', call_space=False)

    def find_first_id(self):
        return self.driver.find_element_by_css_selector(self.TABLE_FIRST_ROW_CSS).get_attribute('id')

    def click_row(self):
        self.driver.find_element_by_css_selector(self.TABLE_FIRST_ROW_CSS).click()

    def click_first_row_checkbox(self):
        self.driver.find_element_by_css_selector(self.TABLE_FIRST_ROW_CHECKBOX_CSS).click()

    def find_query_search_input(self):
        return self.driver.find_element_by_css_selector(self.QUERY_SEARCH_INPUT_CSS)

    def fill_filter(self, filter_string):
        self.fill_text_field_by_css_selector(self.QUERY_SEARCH_INPUT_CSS, filter_string)

    def enter_search(self):
        self.key_down_enter(self.find_query_search_input())

    def open_search_list(self):
        self.key_down_arrow_down(self.find_query_search_input())

    def select_query_by_name(self, query_name):
        el = self.wait_for_element_present_by_xpath(self.QUERY_SEARCH_DROPDOWN_XPATH.format(query_name_text=query_name))
        el.click()

    def select_search_everywhere(self):
        el = self.wait_for_element_present_by_xpath(self.QUERY_SEARCH_EVERYWHERE_XPATH)
        el.click()

    def find_search_value(self):
        return self.find_query_search_input().get_attribute('value')

    def count_entities(self):
        match_count = re.search(r'\((\d+)\)', self.driver.find_element_by_css_selector(self.TABLE_COUNT_CSS).text)
        assert match_count and len(match_count.groups()) == 1
        return int(match_count.group(1))

    def add_query_expression(self):
        self.driver.find_element_by_css_selector(self.QUERY_ADD_EXPRESSION_CSS).click()

    def toggle_left_bracket(self, expression_element):
        expression_element.find_element_by_css_selector(self.QUERY_BRACKET_LEFT_CSS).click()

    def toggle_right_bracket(self, expression_element):
        expression_element.find_element_by_css_selector(self.QUERY_BRACKET_RIGHT_CSS).click()

    def toggle_not(self, expression_element):
        expression_element.find_element_by_css_selector(self.QUERY_NOT_CSS).click()

    def remove_query_expression(self, expression_element):
        expression_element.find_element_by_css_selector(self.QUERY_REMOVE_EXPRESSION_CSS).click()

    def clear_query_wizard(self):
        self.click_button('Clear', partial_class=True)

    def clear_filter(self):
        # Explicit clear needed for Mac - 'fill_filter' will not replace the text
        self.click_query_wizard()
        self.clear_query_wizard()
        self.close_dropdown()

    def find_expressions(self):
        return self.driver.find_elements_by_css_selector(self.QUERY_EXPRESSIONS_CSS)

    def find_rows_with_data(self):
        return self.driver.find_elements_by_xpath(self.TABLE_DATA_ROWS_XPATH)

    def select_page_size(self, page_size):
        self.driver.find_element_by_xpath(self.TABLE_PAGE_SIZE_XPATH.format(page_size_text=page_size)).click()

    def click_sort_column(self, col_name):
        self.driver.find_element_by_xpath(self.TABLE_HEADER_SORT_XPATH.format(col_name_text=col_name)).click()

    def count_sort_column(self, col_name):
        # Return the position of given col_name in list of column headers, 1-based
        try:
            return [element.text.strip() for element in
                    self.driver.find_elements_by_css_selector(self.TABLE_HEADER_CELLS_CSS)].index(col_name) + 1
        except ValueError:
            # Unfortunately col_name is not in the composed list
            return 0

    def get_column_data(self, col_name):
        col_position = self.count_sort_column(col_name)
        if not col_position:
            return []
        return [el.text.strip() for el in
                self.driver.find_elements_by_xpath(self.TABLE_DATA_POS_XPATH.format(data_position=col_position))]

    def get_all_data(self):
        return [data_row.text for data_row in self.find_elements_by_xpath(self.TABLE_DATA_ROWS_XPATH)]

    # retrying because sometimes the table hasn't fully loaded
    @retry(wait_fixed=20, stop_max_delay=3000)
    def get_all_data_proper(self):
        """
        Returns a list of dict where each dict is a dict between a field name (i.e. adapter, asset_name) and
        the respective value
        """
        result = []
        column_names = [x.text for x in self.driver.find_elements_by_css_selector(self.ALL_COLUMN_NAMES_CSS)]
        all_entities = self.driver.find_elements_by_css_selector(self.ALL_ENTITIES_CSS)
        for entity in all_entities:
            if not entity.text.strip():
                # an empty row represents the end
                break

            fields_values = entity.find_elements_by_tag_name('td')
            assert len(fields_values) == len(column_names), 'nonmatching fields'
            fields_values = [x.find_element_by_tag_name('div') for x in fields_values]
            fields_values = [x.get_attribute('title') or x.text for x in fields_values]
            result.append({
                field_name: field_value
                for field_name, field_value in zip(column_names, fields_values)
                if field_name
            })
        return result

    def is_text_in_coloumn(self, col_name, text):
        return any(text in item for item in self.get_column_data(col_name))

    def open_edit_columns(self):
        self.click_button('Edit Columns', partial_class=True)

    def select_column_name(self, col_name):
        self.driver.find_element_by_xpath(self.CHECKBOX_XPATH_TEMPLATE.format(label_text=col_name)).click()

    def close_edit_columns(self):
        self.click_button('Done')

    def select_columns(self, col_names):
        self.open_edit_columns()
        for col_name in col_names:
            self.select_column_name(col_name)
        self.wait_for_spinner_to_end()
        self.close_edit_columns()

    def is_text_error(self, text=None):
        if not text:
            return self.wait_for_element_absent_by_css(self.QUERY_ERROR_CSS)
        return text == self.driver.find_element_by_css_selector(self.QUERY_ERROR_CSS).text

    def click_save_query(self):
        self.driver.find_element_by_id(self.SAVE_QUERY_ID).click()

    def fill_query_name(self, name):
        self.fill_text_field_by_element_id(self.SAVE_QUERY_NAME_ID, name)

    def click_actions_tag_button(self):
        self.driver.find_element_by_css_selector(self.TABLE_ACTIONS_TAG_CSS).click()

    def click_save_query_save_button(self):
        self.driver.find_element_by_id(self.SAVE_QUERY_SAVE_BUTTON_ID).click()

    def fill_showing_results(self, date_to_fill):
        self.fill_text_field_by_css_selector(self.DATEPICKER_INPUT_CSS, date_to_fill.date().isoformat())

    def close_showing_results(self):
        self.driver.find_element_by_css_selector(self.DATEPICKER_OVERLAY_CSS).click()
        self.wait_for_element_absent_by_css(self.DATEPICKER_OVERLAY_CSS)

    def clear_showing_results(self):
        self.driver.find_element_by_css_selector(self.DATEPICKER_CLEAR_CSS).click()

    def run_filter_and_save(self, query_name, query_filter):
        self.fill_filter(query_filter)
        self.enter_search()
        self.wait_for_table_to_load()
        self.click_save_query()
        self.fill_query_name(query_name)
        self.click_save_query_save_button()

    def customize_view_and_save(self, query_name, page_size, sort_field, toggle_columns, query_filter):
        self.select_page_size(page_size)
        self.wait_for_table_to_load()
        self.click_sort_column(sort_field)
        self.wait_for_table_to_load()
        self.select_columns(toggle_columns)
        self.run_filter_and_save(query_name, query_filter)

    def execute_saved_query(self, query_name):
        self.fill_filter(query_name)
        self.open_search_list()
        self.select_query_by_name(query_name)
        self.wait_for_table_to_load()

    def remove_selected(self):
        self.find_element_by_text(self.REMOVE_BUTTON).click()

    def approve_remove_selected(self):
        self.find_element_by_text(self.DELETE_BUTTON).click()

    def click_notes_tab(self):
        self.driver.find_element_by_css_selector(self.NOTES_TAB_CSS).click()

    def fill_save_note(self, note_text, toast_text):
        self.fill_text_field_by_css_selector('.text-input', note_text)
        self.click_button(self.SAVE_BUTTON)
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS)
        self.wait_for_toaster(toast_text)

    def create_note(self, note_text):
        self.click_button('+ Note')
        self.fill_save_note(note_text, self.NOTES_CREATED_TOASTER)

    def edit_note(self, note_text):
        self.click_row()
        self.fill_save_note(note_text, self.NOTES_EDITED_TOASTER)

    def remove_note(self):
        self.click_first_row_checkbox()
        self.remove_selected()
        self.approve_remove_selected()
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS)

    def find_row_readonly(self):
        return self.driver.find_elements_by_css_selector('.x-row:not(.clickable)')
