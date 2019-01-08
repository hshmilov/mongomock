import re

import requests
from retrying import retry
from selenium.common.exceptions import NoSuchElementException

from axonius.utils.parsing import parse_date, parse_date_with_timezone
from ui_tests.pages.page import Page


class EntitiesPage(Page):
    DROPDOWN_TEXT_BOX_CSS = 'div.x-search-input.x-select-search > input'
    DROPDOWN_SELECTED_OPTIONS_CSS = 'div.x-select-options'
    DROPDOWN_SELECTED_OPTION_CSS = 'div.x-select-options > div.x-select-option'

    EDIT_COLUMNS_ADAPTER_DROPDOWN_CSS = 'div.x-dropdown.x-select.x-select-symbol'
    QUERY_WIZARD_ID = 'query_wizard'
    QUERY_EXPRESSIONS_CSS = '.x-filter .x-expression'
    QUERY_CONDITIONS_CSS = '.x-condition'
    QUERY_FIELD_DROPDOWN_CSS = '.x-dropdown.x-select.field-select'
    QUERY_ADAPTER_DROPDOWN_CSS = '.x-select-typed-field .x-dropdown.x-select.x-select-symbol'
    QUERY_COMP_OP_DROPDOWN_CSS = 'div.x-select.expression-comp'
    QUERY_DATE_PICKER_CSS = '.expression-value .md-datepicker .md-input'
    QUERY_VALUE_COMPONENT_CSS = '.expression-value'
    QUERY_SEARCH_INPUT_CSS = '#query_list .input-value'
    QUERY_SEARCH_DROPDOWN_XPATH = '//div[@id=\'query_select\']//div[text()=\'{query_name_text}\']'
    QUERY_SEARCH_EVERYWHERE_XPATH = '//div[@class=\'query-quick\']//div[contains(text(), \'Search in table:\')]'
    QUERY_ADD_EXPRESSION_CSS = '.x-filter .footer .x-btn'
    QUERY_NEST_EXPRESSION_CSS = '.x-filter .x-expression .x-btn.expression-nest'
    QUERY_BRACKET_LEFT_CSS = '.expression-bracket-left'
    QUERY_BRACKET_RIGHT_CSS = '.expression-bracket-right'
    QUERY_NOT_CSS = '.expression-not'
    QUERY_OBJ_CSS = '.expression-obj'
    QUERY_REMOVE_EXPRESSION_CSS = '.x-btn.expression-remove'
    QUERY_LOGIC_DROPDOWN_CSS = 'div.x-select.x-select-logic'
    QUERY_ERROR_CSS = '.x-filter .error-text'
    QUERY_COMP_EXISTS = 'exists'
    QUERY_COMP_CONTAINS = 'contains'
    QUERY_COMP_EQUALS = 'equals'
    QUERY_COMP_SUBNET = 'subnet'
    QUERY_COMP_SIZE = 'size'
    QUERY_LOGIC_AND = 'and'
    QUERY_LOGIC_OR = 'or'
    OUTDATED_TOGGLE_CSS = 'div.md-switch.md-theme-default > div > div'
    TABLE_SELECT_ALL_CHECKBOX_CSS = 'thead .x-checkbox'
    TABLE_COUNT_CSS = '.x-table-header .x-title .count'
    TABLE_FIRST_ROW_CSS = 'tbody .x-row.clickable'
    TABLE_SECOND_ROW_CSS = 'tbody .x-row.clickable:nth-child(2)'
    TABLE_FIRST_CELL_CSS = f'{TABLE_FIRST_ROW_CSS} td:nth-child(2)'
    TABLE_ROW_CHECKBOX_CSS = 'tbody .x-row.clickable:nth-child({child_index}) td:nth-child(1) .x-checkbox'
    TABLE_FIRST_ROW_TAG_CSS = f'{TABLE_FIRST_ROW_CSS} td:last-child'
    TABLE_DATA_ROWS_XPATH = '//tr[@id]'
    TABLE_PAGE_SIZE_XPATH = '//div[@class=\'x-pagination\']/div[@class=\'x-sizes\']/div[text()=\'{page_size_text}\']'
    TABLE_HEADER_XPATH = '//*[@id="app"]/div/div[2]/div/div[3]/div[1]/div[3]/table/thead/tr'
    VALUE_ADAPTERS_JSON = 'JSON File'
    VALUE_ADAPTERS_AD = 'Active Directory'
    TABLE_HEADER_CELLS_CSS = 'th'
    TABLE_HEADER_SORT_XPATH = '//th[contains(@class, \'sortable\') and contains(text(), \'{col_name_text}\')]'
    TABLE_DATA_POS_XPATH = '//tr[@id]/td[position()={data_position}]'
    TABLE_COLUMNS_MENU_CSS = '.x-field-menu-filter'
    TABLE_ACTIONS_TAG_CSS = 'div.content.w-sm > div > div:nth-child(1) > div.item-content'
    TABLE_ACTIONS_DELETE_CSS = 'div.content.w-sm > div > div:nth-child(2) > div.item-content'
    TABLE_ACTION_ITEM_XPATH = '//div[@class=\'x-actions\']//div[@class=\'item-content\' and text()=\'{action}\']'
    SAVE_QUERY_ID = 'query_save'
    SAVE_QUERY_NAME_ID = 'saveName'
    SAVE_QUERY_SAVE_BUTTON_ID = 'query_save_confirm'
    ALL_COLUMN_NAMES_CSS = 'thead>tr>th'
    ALL_ENTITIES_CSS = 'tbody>tr'

    JSON_ADAPTER_FILTER = 'adapters == "json_file_adapter"'
    AD_ADAPTER_FILTER = 'adapters == "active_directory_adapter"'
    AD_WMI_ADAPTER_FILTER = f'{AD_ADAPTER_FILTER} and adapters_data.general_info.id == exists(true)'

    DATEPICKER_INPUT_CSS = '.md-datepicker .md-input'
    DATEPICKER_OVERLAY_CSS = '.md-datepicker-overlay'

    NOTES_CONTENT_CSS = '.x-entity-notes'

    NOTES_TAB_CSS = 'li#notes'
    TAGS_TAB_CSS = 'li#tags'
    CUSTOM_DATA_TAB_CSS = 'li#gui_unique'

    NOTES_CREATED_TOASTER = 'New note was created'
    NOTES_EDITED_TOASTER = 'Existing note was edited'
    NOTES_REMOVED_TOASTER = 'Notes were removed'
    NOTES_SEARCH_INUPUT_CSS = '#search-notes .input-value'
    NOTES_SEARCH_BY_TEXT = 'div[title={note_text}]'

    CONFIG_ADVANCED_TEXT = 'View advanced'
    ADVANCED_VIEW_RAW_FIELD = '"raw":'
    CONFIG_BASIC_TEXT = 'View basic'

    ID_FIELD = 'ID'
    ENTITY_FIELD_VALUE_XPATH = '//div[@class=\'object\' and child::label[text()=\'{field_name}\']]/div'

    CUSTOM_DATA_EDIT_BTN = 'Edit Fields'
    CUSTOM_DATA_PREDEFINED_FIELD_CSS = '.custom-fields .fields-item .x-select.item-name'
    CUSTOM_DATA_NEW_FIELD_TYPE_CSS = '.custom-fields .fields-item .x-select.item-type'
    CUSTOM_DATA_NEW_FIELD_NAME_CSS = '.custom-fields .fields-item input.item-name'
    CUSTOM_DATA_FIELD_VALUE_CSS = '.custom-fields .fields-item .item-value'
    CUSTOM_DATA_FIELD_ITEM = '.custom-fields .fields-item'
    CUSTOM_DATA_ERROR_CSS = '.footer .error-text'
    CUSTOM_DATA_BULK_CONTAINER_CSS = '.x-actions'

    @property
    def url(self):
        raise NotImplementedError

    @property
    def root_page_css(self):
        raise NotImplementedError

    def click_query_wizard(self):
        self.driver.find_element_by_id(self.QUERY_WIZARD_ID).click()

    def select_query_field(self, text, parent=None, partial_text=True):
        self.select_option(self.QUERY_FIELD_DROPDOWN_CSS,
                           self.DROPDOWN_TEXT_BOX_CSS,
                           self.DROPDOWN_SELECTED_OPTION_CSS,
                           text,
                           parent=parent,
                           partial_text=partial_text)

    def get_all_fields_in_field_selection(self):
        self.driver.find_element_by_css_selector(self.QUERY_FIELD_DROPDOWN_CSS).click()
        try:
            for element in self.driver.find_elements_by_css_selector('.x-select-option'):
                yield element.text
        finally:
            self.driver.find_element_by_css_selector(self.QUERY_FIELD_DROPDOWN_CSS).click()

    def get_query_field(self):
        return self.driver.find_element_by_css_selector(self.QUERY_FIELD_DROPDOWN_CSS).text

    def select_query_adapter(self, text, parent=None):
        self.select_option(self.QUERY_ADAPTER_DROPDOWN_CSS,
                           self.DROPDOWN_TEXT_BOX_CSS,
                           self.DROPDOWN_SELECTED_OPTION_CSS,
                           text,
                           parent=parent)

    def open_query_adapters_list(self):
        self.driver.find_element_by_css_selector(self.QUERY_ADAPTER_DROPDOWN_CSS).click()

    def get_query_adapters_list(self):
        self.open_query_adapters_list()
        return self.get_adapters_list()

    def open_edit_columns_adapters_list(self):
        self.driver.find_element_by_css_selector(self.EDIT_COLUMNS_ADAPTER_DROPDOWN_CSS).click()

    def get_edit_columns_adapters_list(self):
        self.open_edit_columns_adapters_list()
        return self.get_adapters_list()

    def get_adapters_list(self):
        adapters_list = self.driver.find_element_by_css_selector(self.DROPDOWN_SELECTED_OPTIONS_CSS).text.split('\n')
        adapters_list.remove('General')
        return adapters_list

    def select_query_comp_op(self, text, parent=None):
        self.select_option_without_search(self.QUERY_COMP_OP_DROPDOWN_CSS,
                                          self.DROPDOWN_SELECTED_OPTION_CSS,
                                          text,
                                          parent=parent)

    def fill_query_wizard_date_picker(self, date_value, parent=None):
        self.fill_text_field_by_css_selector(self.QUERY_DATE_PICKER_CSS,
                                             parse_date(date_value).date().isoformat(), context=parent)

    def get_query_comp_op(self):
        return self.driver.find_element_by_css_selector(self.QUERY_COMP_OP_DROPDOWN_CSS).text

    def fill_query_value(self, text, parent=None):
        self.fill_text_field_by_css_selector(self.QUERY_VALUE_COMPONENT_CSS, text, context=parent)

    def select_query_value(self, text, parent=None):
        self.select_option(self.QUERY_VALUE_COMPONENT_CSS,
                           self.DROPDOWN_TEXT_BOX_CSS,
                           self.DROPDOWN_SELECTED_OPTION_CSS,
                           text, parent=parent)

    def get_query_value(self):
        el = self.wait_for_element_present_by_css(self.QUERY_VALUE_COMPONENT_CSS)
        return el.get_attribute('value')

    def select_query_logic_op(self, text, parent=None):
        self.select_option_without_search(self.QUERY_LOGIC_DROPDOWN_CSS, self.DROPDOWN_SELECTED_OPTION_CSS, text,
                                          parent=parent)

    def click_wizard_outdated_toggle(self):
        self.driver.find_element_by_css_selector(self.OUTDATED_TOGGLE_CSS).click()

    def click_search(self):
        self.click_button('Search', call_space=False)

    def find_first_id(self):
        return self.driver.find_element_by_css_selector(self.TABLE_FIRST_ROW_CSS).get_attribute('id')

    def click_row(self):
        self.driver.find_element_by_css_selector(self.TABLE_FIRST_ROW_CSS).click()
        self.wait_for_spinner_to_end()

    def click_row_checkbox(self, index=1):
        self.driver.find_element_by_css_selector(self.TABLE_ROW_CHECKBOX_CSS.format(child_index=index)).click()

    def click_specific_row_checkbox(self, field_name, field_value):
        values = self.get_column_data(field_name)
        row_num = values.index(field_value)
        self.click_row_checkbox(row_num + 1)

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

    def toggle_not(self, expression_element=None):
        if not expression_element:
            expression_element = self.driver
        expression_element.find_element_by_css_selector(self.QUERY_NOT_CSS).click()

    def toggle_obj(self, expression_element):
        expression_element.find_element_by_css_selector(self.QUERY_OBJ_CSS).click()

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

    def find_conditions(self, parent=None):
        if not parent:
            parent = self.driver
        return parent.find_elements_by_css_selector(self.QUERY_CONDITIONS_CSS)

    def add_query_obj_condition(self, parent=None):
        if not parent:
            parent = self.driver
        parent.find_element_by_css_selector(self.QUERY_NEST_EXPRESSION_CSS).click()

    def find_rows_with_data(self):
        return self.driver.find_elements_by_xpath(self.TABLE_DATA_ROWS_XPATH)

    def select_page_size(self, page_size):
        self.driver.find_element_by_xpath(self.TABLE_PAGE_SIZE_XPATH.format(page_size_text=page_size)).click()

    def click_sort_column(self, col_name):
        self.driver.find_element_by_xpath(self.TABLE_HEADER_SORT_XPATH.format(col_name_text=col_name)).click()

    def get_columns_header_text(self):
        headers = self.driver.find_element_by_xpath(self.TABLE_HEADER_XPATH)
        header_columns = headers.find_elements_by_tag_name('th')
        return [head.text for head in header_columns if head.text]

    def count_sort_column(self, col_name, parent=None):
        # Return the position of given col_name in list of column headers, 1-based
        if not parent:
            parent = self.driver

        try:
            return [element.text.strip() for element in
                    parent.find_elements_by_css_selector(self.TABLE_HEADER_CELLS_CSS)].index(col_name) + 1
        except ValueError:
            # Unfortunately col_name is not in the composed list
            return 0

    def get_note_by_text(self, note_text):
        return self.driver.find_element_by_css_selector(self.NOTES_SEARCH_BY_TEXT.format(note_text=note_text))

    def get_notes_column_data(self, col_name):
        parent = self.driver.find_element_by_css_selector(self.NOTES_CONTENT_CSS)
        return self.get_column_data(col_name, parent)

    def get_column_data(self, col_name, parent=None):
        if not parent:
            parent = self.driver

        col_position = self.count_sort_column(col_name, parent)
        if not col_position:
            return []
        return [el.text.strip() for el in
                parent.find_elements_by_xpath(self.TABLE_DATA_POS_XPATH.format(data_position=col_position))]

    def get_all_data(self):
        return [data_row.text for data_row in self.find_elements_by_xpath(self.TABLE_DATA_ROWS_XPATH)]

    def select_all_page_rows_checkbox(self):
        self.driver.find_element_by_css_selector(self.TABLE_SELECT_ALL_CHECKBOX_CSS).click()

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
        self.click_button('Edit Columns', partial_class=True, should_scroll_into_view=False)

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

    def is_query_error(self, text=None):
        if not text:
            return self.wait_for_element_absent_by_css(self.QUERY_ERROR_CSS)
        return text == self.driver.find_element_by_css_selector(self.QUERY_ERROR_CSS).text

    def click_save_query(self):
        self.driver.find_element_by_id(self.SAVE_QUERY_ID).click()

    def fill_query_name(self, name):
        self.fill_text_field_by_element_id(self.SAVE_QUERY_NAME_ID, name)

    def click_actions_tag_button(self):
        self.driver.find_element_by_css_selector(self.TABLE_ACTIONS_TAG_CSS).click()

    def open_edit_tags(self):
        self.click_button('Edit Tags', partial_class=True)

    def click_save_query_save_button(self):
        self.driver.find_element_by_id(self.SAVE_QUERY_SAVE_BUTTON_ID).click()
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS)

    def fill_showing_results(self, date_to_fill):
        self.fill_text_field_by_css_selector(self.DATEPICKER_INPUT_CSS, date_to_fill.date().isoformat())

    def close_showing_results(self):
        try:
            self.driver.find_element_by_css_selector(self.DATEPICKER_OVERLAY_CSS).click()
            self.wait_for_element_absent_by_css(self.DATEPICKER_OVERLAY_CSS)
        except NoSuchElementException:
            # Already closed
            pass

    def click_remove_sign(self):
        self.click_button('X', partial_class=True, should_scroll_into_view=False)

    def clear_showing_results(self):
        self.click_remove_sign()

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

    def click_tags_tab(self):
        self.driver.find_element_by_css_selector(self.TAGS_TAB_CSS).click()

    def click_custom_data_tab(self):
        self.driver.find_element_by_css_selector(self.CUSTOM_DATA_TAB_CSS).click()

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
        self.click_row_checkbox()
        self.remove_selected()
        self.approve_remove_selected()
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS)

    def find_notes_row_readonly(self):
        parent = self.driver.find_element_by_css_selector(self.NOTES_CONTENT_CSS)
        return self.find_row_readonly(parent)

    def find_row_readonly(self, parent=None):
        if not parent:
            parent = self.driver
        return parent.find_elements_by_css_selector('.x-row:not(.clickable)')

    def search_note(self, search_text):
        self.fill_text_field_by_css_selector(self.NOTES_SEARCH_INUPUT_CSS, search_text)

    def generate_csv(self, entity_type, fields, filters):
        session = requests.Session()
        cookies = self.driver.get_cookies()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])
        return session.get(
            f'https://127.0.0.1/api/{entity_type}/csv?fields={fields}&filter={filters}')

    def assert_csv_match_ui_data(self, result):
        all_csv_rows = result.text.split('\r\n')
        csv_headers = all_csv_rows[0].split(',')
        csv_data_rows = all_csv_rows[1:-1]

        ui_headers = self.get_columns_header_text()
        ui_data_rows = [row.split('\n') for row in self.get_all_data()]
        # we don't writ image to csv
        if 'Image' in ui_headers:
            ui_headers.remove('Image')

        assert sorted(ui_headers) == sorted(csv_headers)
        # for every cell in the ui_data_rows we check if its in the csv_data_row
        # the reason we check it is because the csv have more columns with data
        # than the columns that we getting from the ui (boolean in the ui are represented by the css)
        for index, data_row in enumerate(csv_data_rows):
            for ui_data_row in ui_data_rows[index]:
                ui_row = ui_data_row
                parsed_date = parse_date_with_timezone(ui_row, 'Israel')
                if parsed_date:
                    parsed_date = parse_date(parsed_date)
                    ui_row = parsed_date.strftime('%Y-%m-%d %H:%M:%S')
                assert ui_row in data_row

    def query_json_adapter(self):
        self.run_filter_query(self.JSON_ADAPTER_FILTER)

    def run_filter_query(self, filter_value):
        self.fill_filter(filter_value)
        self.enter_search()
        self.wait_for_table_to_load()

    def open_delete_dialog(self):
        self.click_button(self.ACTIONS_BUTTON, partial_class=True)
        self.driver.find_element_by_css_selector(self.TABLE_ACTIONS_DELETE_CSS).click()

    def read_delete_dialog(self):
        return self.wait_for_element_present_by_css('.x-actions .modal-body .warn-delete').text

    def confirm_delete(self):
        self.click_button(self.DELETE_BUTTON)

    def refresh_table(self):
        self.enter_search()
        self.wait_for_table_to_load()

    def find_advanced_view(self):
        return self.get_button(self.CONFIG_ADVANCED_TEXT, partial_class=True)

    def click_advanced_view(self):
        self.find_advanced_view().click()

    def find_basic_view(self):
        return self.get_button(self.CONFIG_BASIC_TEXT, partial_class=True)

    def click_basic_view(self):
        self.find_basic_view().click()

    def load_notes(self, entities_filter=None):
        self.switch_to_page()
        if entities_filter:
            self.fill_filter(entities_filter)
            self.enter_search()
        self.wait_for_table_to_load()
        self.click_row()
        self.wait_for_spinner_to_end()
        self.click_notes_tab()

    def load_custom_data(self, entities_filter=None):
        self.switch_to_page()
        if entities_filter:
            self.fill_filter(entities_filter)
            self.enter_search()
        self.wait_for_table_to_load()
        self.click_row()
        self.wait_for_spinner_to_end()
        self.click_custom_data_tab()

    def get_entity_id(self):
        return self.find_element_by_text(self.ID_FIELD).text

    def find_custom_data_edit(self):
        return self.get_button(self.CUSTOM_DATA_EDIT_BTN)

    def click_custom_data_edit(self):
        return self.find_custom_data_edit().click()

    def click_custom_data_add_predefined(self):
        return self.click_button('+ Predefined field', partial_class=True)

    def click_custom_data_add_new(self):
        return self.click_button('+ New field', partial_class=True)

    def find_custom_data_save(self, context=None):
        return self.get_button(self.SAVE_BUTTON, partial_class=True, context=context)

    def find_custom_fields_items(self):
        return self.driver.find_elements_by_css_selector(self.CUSTOM_DATA_FIELD_ITEM)

    def find_custom_data_predefined_field(self, parent=None):
        if not parent:
            parent = self.driver
        return parent.find_element_by_css_selector(self.CUSTOM_DATA_PREDEFINED_FIELD_CSS)

    def find_custom_data_new_field_name(self, parent=None):
        if not parent:
            parent = self.driver
        return parent.find_element_by_css_selector(self.CUSTOM_DATA_NEW_FIELD_NAME_CSS)

    def find_custom_data_new_field_type(self, parent=None):
        if not parent:
            parent = self.driver
        return parent.find_element_by_css_selector(self.CUSTOM_DATA_NEW_FIELD_TYPE_CSS)

    def find_custom_data_value(self, parent=None):
        if not parent:
            parent = self.driver
        return parent.find_element_by_css_selector(self.CUSTOM_DATA_FIELD_VALUE_CSS)

    def select_custom_data_field(self, field_name, parent=None):
        self.select_option(self.CUSTOM_DATA_PREDEFINED_FIELD_CSS, self.DROPDOWN_TEXT_BOX_CSS,
                           self.DROPDOWN_SELECTED_OPTION_CSS, field_name, parent)

    def select_custom_data_field_type(self, field_type, parent=None):
        self.select_option(self.CUSTOM_DATA_NEW_FIELD_TYPE_CSS, self.DROPDOWN_TEXT_BOX_CSS,
                           self.DROPDOWN_SELECTED_OPTION_CSS, field_type, parent)

    def fill_custom_data_field_name(self, field_name, parent=None):
        self.fill_text_field_by_css_selector(self.CUSTOM_DATA_NEW_FIELD_NAME_CSS, field_name, parent)

    def fill_custom_data_value(self, field_value, parent=None):
        self.fill_text_field_by_css_selector(self.CUSTOM_DATA_FIELD_VALUE_CSS, field_value, parent)

    def save_custom_data(self, context=None):
        self.find_custom_data_save(context).click()
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS)

    def clear_custom_data_field(self):
        self.click_remove_sign()

    def is_custom_error(self, error_text=None):
        if not error_text:
            return self.wait_for_element_absent_by_css(self.CUSTOM_DATA_ERROR_CSS)
        return error_text == self.driver.find_element_by_css_selector(self.CUSTOM_DATA_ERROR_CSS).text

    def open_custom_data_bulk(self):
        self.click_button('Actions', partial_class=True, should_scroll_into_view=False)
        self.driver.find_element_by_xpath(self.TABLE_ACTION_ITEM_XPATH.format(action='Add custom data...')).click()
