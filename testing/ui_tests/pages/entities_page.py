import codecs
import logging
import re
import time
import typing

import requests
from retrying import retry
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement

from axonius.utils.datetime import parse_date
from axonius.utils.parsing import normalize_timezone_date
from axonius.utils.wait import wait_until
from axonius.utils.serial_csv.constants import (MAX_ROWS_LEN, CELL_JOIN_DEFAULT)
from ui_tests.pages.page import Page, TableRow
from ui_tests.tests.ui_consts import AD_ADAPTER_NAME, COMP_CONTAINS, COMP_REGEX, COMP_EQUALS, COMP_IN, \
    JSON_ADAPTER_FILTER

TABLE_COUNT_CSS = '.table-header .table-title .count'
CSV_TIMEOUT = 60 * 60

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=C0302,no-member,no-self-use


class EntitiesPage(Page):
    EXPORT_CSV_CONFIG_MODAL_ID = 'csv_export_config'
    EXPORT_CSV_DELIMITER_ID = 'csv_delimiter'
    EXPORT_CSV_MAX_ROWS_ID = 'csv_max_rows'
    EXPORT_CSV_BUTTON_TEXT = 'Export CSV'
    EXPORT_CSV_LOADING_TEXT = 'Exporting...'
    EDIT_COLUMNS_ADAPTER_DROPDOWN_CSS = '.x-dropdown.x-select.x-select-symbol'
    EDIT_COLUMNS_SELECT_XPATH = '//div[@class=\'field-list {list_type}\']' \
                                '//div[@class=\'x-checkbox\' and .//text()=\'{col_title}\']'
    DISPLAYED_COLUMNS_MENU_XPATH = '//div[@class=\'field-list view\']//div[@class=\'x-checkbox\']'

    QUERY_WIZARD_ID = 'query_wizard'
    QUERY_EXPRESSIONS_CSS = '.x-filter .x-expression'
    QUERY_CONDITIONS_CSS = '.x-condition__child'
    QUERY_FIELD_DROPDOWN_CSS = '.x-select.field-select'
    QUERY_CONDITIONS_OPTIONS_CSS = '.x-select-options'
    QUERY_ADAPTER_DROPDOWN_CSS = '.x-select-typed-field .x-dropdown.x-select.x-select-symbol'
    QUERY_COMP_OP_DROPDOWN_CSS = 'div.x-select.expression-comp'
    QUERY_DATE_PICKER_CONTAINER_CSS = '.x-condition-function .x-date-edit'
    QUERY_VALUE_COMPONENT_INPUT_CSS = '.x-condition-function .argument input'
    QUERY_VALUE_COMPONENT_CSS = '.x-condition-function .argument'
    QUERY_VALUE_FIELD_COMPARISON_COMPONENT_CSS = '.x-condition-function-field-comparison .argument'
    QUERY_SEARCH_INPUT_CSS = '#query_list .input-value'
    EXPRESSION_INPUT_INT_TRIGGER_CSS = '.x-condition-function .argument .x-select-trigger'
    EXP1_TRIGGER_CSS = '.x-condition-function .argument > .trigger.arrow'
    EXP2_INPUT_CSS = '.x-condition-function .argument .content.expand .x-search-input.x-select-search .input-value'
    QUERY_ADAPTER_DROPDOWN_SECONDARY_OPTIONS_CSS = 'div.x-select-options > .x-secondary-select-content >' \
                                                   '.x-select-options'
    SAVED_QUERY_OPTIONS_CSS = '.x-condition-function .argument .x-select-options .x-select-option'

    QUERY_SEARCH_DROPDOWN_XPATH = '//div[@id=\'query_select\']//div[contains(text(),\'{query_name_text}\')]'
    QUERY_SEARCH_EVERYWHERE_CSS = 'div.x-menu>div>.item-content'
    QUERY_ADD_EXPRESSION_CSS = '.x-filter .footer .x-button'
    QUERY_NEST_EXPRESSION_CSS = '.x-expression .expression-nest'
    QUERY_BRACKET_LEFT_CSS = '.expression-bracket-left'
    QUERY_BRACKET_RIGHT_CSS = '.expression-bracket-right'
    QUERY_NOT_CSS = '.expression-not'
    QUERY_CONTEXT_CSS = '.expression-context'
    QUERY_ASSET_ENTITY_ADAPTER_CSS = '.x-condition-asset-entity .parent-field .x-select-symbol'
    QUERY_ASSET_ENTITY_CHILDREN_CSS = '.x-condition-asset-entity-child'
    QUERY_ASSET_ENTITY_FIELD_CSS = '.child-field .x-select'
    QUERY_REMOVE_EXPRESSION_CSS = '.x-button.expression-remove'
    QUERY_LOGIC_DROPDOWN_CSS = 'div.x-select.x-select-logic'
    QUERY_ERROR_CSS = '.x-filter .error-text'
    OUTDATED_TOGGLE_CSS = 'div.md-switch.md-theme-default > div > div'
    TABLE_CLASS = '.table'
    TABLE_SELECT_ALL_CURRENT_PAGE_CHECKBOX_CSS = 'thead .x-checkbox'
    TABLE_SELECT_ALL_CSS = 'div.selection > .x-button.ant-btn-link'
    TABLE_SELECTED_COUNT_CSS = '.table-header > .table-title > .selection > div'
    TABLE_SELECT_ALL_BUTTON_CSS = '.table-header > .table-title > .selection > button'
    TABLE_FIRST_ROW_CSS = 'tbody .x-table-row.clickable'
    TABLE_FIRST_ROW_DATA_CSS = f'{TABLE_FIRST_ROW_CSS} td:not(.top)'
    TABLE_FIRST_ROW_TAG_CSS = f'{TABLE_FIRST_ROW_CSS} td:last-child'
    TABLE_ROW_EXPAND_CSS = 'tbody .x-table-row.clickable:nth-child({child_index}) td:nth-child(2) .x-icon'
    TABLE_CELL_CSS = 'tbody .x-table-row.clickable td:nth-child({cell_index})'
    TABLE_CELL_EXPAND_CSS = 'tbody .x-table-row.clickable:nth-child({row_index}) td:nth-child({cell_index}) .x-icon'
    TABLE_CELL_HOVER_REMAINDER_CSS = 'tbody .x-table-row.clickable:nth-child({row_index}) td:nth-child({cell_index}) ' \
                                     '.x-data .x-slice .remainder'
    TABLE_DATA_ROWS_TEXT_CSS = '.x-data > div'
    TABLE_SCHEMA_CUSTOM = '//div[contains(@class, \'x-schema-custom__content\')]'
    TABLE_FIELD_ROWS_XPATH_WITH_IDS = '//div[contains(@class, \'x-tabs\')]//div[contains(@class, \'x-tab active\')]'\
                                      '//div[@class=\'x-table\']//tr[@class=\'x-table-row\' and @id]'
    TABLE_PAGE_SIZE_XPATH = '//div[@class=\'x-pagination\']/div[@class=\'x-sizes\']/div[text()=\'{page_size_text}\']'
    TABLE_PAGE_SELECT_XPATH = '//div[@class=\'x-pagination\']/div[@class=\'x-pages\']/div'
    TABLE_PAGE_ACTIVE_XPATH = '//div[@class=\'x-pagination\']/div[@class=\'x-pages\']/div[@class=\'x-link active\']'
    TABLE_HEADER_FIELD_XPATH = '//div[contains(@class, \'x-entity-general\')]//div[contains(@class, \'x-tab active\')]'\
                               '//div[@class=\'x-table\']//thead/tr'
    NAME_ADAPTERS_JSON = 'json_file_adapter'
    NAME_ADAPTERS_AD = 'active_directory_adapter'
    VALUE_ADAPTERS_GENERAL = 'Aggregated'
    TABLE_HEADER_CELLS_XPATH = '//th[child::img[contains(@class, \'logo\')]]'
    TABLE_HEADER_BY_NAME_XPATH = '//th[contains(@class, \'x-table-head\') and contains(., \'{col_name_text}\')]'

    TABLE_DATA_SLICER_TYPE_XPATH = f'{Page.TABLE_DATA_XPATH}//div[@class=\'x-slice\']/div'
    TABLE_DATA_EXPAND_ROW_XPATH = f'{Page.TABLE_DATA_XPATH}//div[@class=\'details-list-container\']'
    TABLE_DATA_EXPAND_CELL_XPATH = '//div[contains(@class, \'ant-popover\')]//*[@class=\'table\']'
    TABLE_DATA_EXPAND_CELL_BODY_XPATH = f'{TABLE_DATA_EXPAND_CELL_XPATH}/tbody'
    TABLE_DATA_IMG_XPATH = './/td[@class=\'table-td-adapters\']//img'

    TABLE_COLUMNS_MENU_CSS = '.x-field-menu-filter'
    TABLE_ACTIONS_DELETE = 'delete'
    TABLE_ACTIONS_LINK_DEVICES = 'link'
    TABLE_ACTIONS_UNLINK_DEVICES = 'unlink'
    TABLE_ACTIONS_CUSTOM_DATA = 'add_custom_data'
    TABLE_ACTIONS_TAG = 'tag'
    TABLE_ACTIONS_ENFORCE_SUB_MENU = 'enforce_options'
    TABLE_ACTIONS_RUN_ENFORCE = 'run_enforce'
    TABLE_ACTIONS_ADD_ENFORCE = 'create_enforce'
    TABLE_ACTIONS_FILTER_OUT = 'filter_out'
    TABLE_ACTION_ITEM_XPATH = \
        '//div[@class=\'actions\']//div[@class=\'item-content\' and contains(text(),\'{action}\')]'
    TABLE_EDIT_COLUMN_MODAL = 'div.x-edit-columns-modal'

    TABLE_OPTIONS_ITEM_XPATH = '//div[@class=\'v-list-item__title\' and text()=\'{option_title}\']'

    SAVE_QUERY_ID = 'query_save'
    SAVE_QUERY_NAME_SELECTOR = '.name-input'
    SAVE_QUERY_PRIVATE_CHECKBOX_ID = 'private_query_checkbox'
    SAVE_QUERY_DESCRIPTION_SELECTOR = '.save-query-dialog textarea'
    SAVE_QUERY_SAVE_BUTTON_ID = 'query_save_confirm'
    SAVE_AS_DROPDOWN_ARROW = '.x-query-state .save-as-dropdown .arrowIcon'
    SAVE_AS_DROPDOWN_DISCARD_ID = 'discardChanges'
    SAVE_AS_DROPDOWN_SAVE_CHANGES_ID = 'saveChanges'
    ALL_ENTITIES_CSS = 'tbody>tr'
    UNSAVED_QUERY_STATUS = '[Unsaved]'
    RANDOM_FILTER_VALUE = 'some random filter'

    STRESSTEST_ADAPTER_FILTER = 'adapters == "stresstest_adapter"'
    PRINTER_DEVICE_FILTER = 'specific_data.data.hostname == "Computer-next-to-printer.TestDomain.test"'
    SPECIFIC_JSON_ADAPTER_FILTER = 'adapters_data.json_file_adapter.username == "ofri" or ' \
                                   'adapters_data.json_file_adapter.hostname == "CB First"'
    AD_ADAPTER_FILTER = 'adapters == "active_directory_adapter"'
    AD_WMI_ADAPTER_FILTER = f'{AD_ADAPTER_FILTER} and adapters_data.wmi_adapter.id == exists(true)'

    NOTES_CONTENT_CSS = '.x-entity-notes'
    NOTES_TAB_CSS = 'li#notes'
    TAGS_TAB_CSS = 'li#tags'
    CUSTOM_DATA_TAB_CSS = 'li#gui_unique'
    GENERAL_DATA_TAB_TITLE = 'Aggregated'
    ADAPTERS_DATA_TAB_TITLE = 'Adapter Connections'
    ADAPTERS_DATA_TAB_CSS = '.x-entity-adapters'
    ENFORCEMENT_DATA_TAB_TITLE = 'Enforcement Tasks'
    EXTENDED_DATA_TAB_TITLE = 'Extended Data'

    NOTES_CREATED_TOASTER = 'New note was created'
    NOTES_EDITED_TOASTER = 'Existing note was edited'
    NOTES_REMOVED_TOASTER = 'Notes were removed'
    NOTES_SEARCH_INUPUT_CSS = '#search-notes .input-value'
    NOTES_SEARCH_BY_TEXT_XPATH = '//div[text()=\'{note_text}\']'

    CONFIG_ADVANCED_TEXT_CSS = '.x-entity-adapters>div.x-tabs>div.body>div.active>div.header>button.ant-btn-link'
    ADVANCED_VIEW_RAW_FIELD = 'raw:'
    CONFIG_BASIC_TEXT = 'View Basic'

    ID_FIELD = 'ID'
    ENTITY_FIELD_VALUE_XPATH = '//div[@class=\'object\' and child::label[text()=\'{field_name}\']]/div'

    AD_ORGANIZATIONAL_UNIT_FIELD = 'AD Organizational Unit'
    AD_ORGANIZATIONAL_UNIT_COLUMN = 'Organizational Unit'

    CUSTOM_DATA_EDIT_BTN = 'Edit Fields'
    CUSTOM_DATA_PREDEFINED_FIELD_CSS = '.custom-fields .fields-item .x-select.item-name'
    CUSTOM_DATA_NEW_FIELD_TYPE_CSS = '.custom-fields .fields-item .x-select.item-type'
    CUSTOM_DATA_NEW_FIELD_NAME_CSS = '.custom-fields .fields-item input.item-name'
    CUSTOM_DATA_FIELD_VALUE_CSS = '.custom-fields .fields-item .item-value'
    CUSTOM_DATA_FIELD_STRING_VALUE_CSS = '.custom-fields .fields-item .item-value input'
    CUSTOM_DATA_FIELD_ITEM = '.custom-fields .fields-item'
    CUSTOM_DATA_ERROR_CSS = '.x-entity-custom-fields .footer .error-text'
    CUSTOM_DATA_BULK_CONTAINER_CSS = '.actions'

    ENFORCEMENT_RESULTS_TITLE_END = '- Task 1'
    ENFORCEMENT_RESULTS_SUBTITLE = 'results of "{action_name}" action'
    MISSING_EMAIL_SETTINGS_TEXT = 'In order to send alerts through mail, configure it under settings'
    ENFORCEMENT_SEARCH_INPUT = '.body .x-tabs .body .x-tab.active .x-search-input input'
    TASKS_TAB_TASK_NAME_XPATH = '//div[contains(@class, \'x-tab active\')]//table//a[.//text()=\'{task_name}\']'

    FILTER_ADAPTERS_CSS = '.filter-adapters'
    FILTER_ADAPTERS_BOX_CSS = '.x-secondary-select-content'
    FILTERED_ADAPTER_ICON_CSS = '.img-filtered'

    REMAINDER_CSS = '.x-data .array.inline .item .remainder>span'
    TOOLTIP_CSS = '.ant-popover'
    TOOLTIP_TABLE_HEAD_CSS = f'{TOOLTIP_CSS} .x-table .table thead .clickable th'
    TOOLTIP_TABLE_DATA_CSS = f'{TOOLTIP_CSS} .x-table .table tbody .x-table-row td'
    OLD_TOOLTIP_TABLE_DATA_CSS = f'.x-tooltip .x-table .table tbody .x-table-row td'
    ADAPTERS_TOOLTIP_TABLE_CSS = f'.x-tooltip .table'

    ACTIVE_TAB_TABLE_ROWS = '.body .x-tabs.vertical .body .x-tab.active .x-table-row'
    ACTIVE_TAB_TABLE_ROWS_HEADERS = '.body .x-tabs.vertical .body .x-tab.active .x-table thead th'
    MSG_ERROR_QUERY_WIZARD = 'A value to compare is needed to add expression to the filter'

    FIELD_UPDATED_BY = 'Updated By'
    FIELD_LAST_UPDATED = 'Last Updated'
    FIELD_TAGS = 'Tags'

    QUERY_MODAL_OVERLAY = '.v-overlay'

    EDIT_USER_COLUMN_BUTTON_ID = 'edit_user_columns'
    RESET_COLS_USER_BUTTON_ID = 'reset_user_default'
    RESET_COLS_SYSTEM_BUTTON_ID = 'reset_system_default'
    EDIT_SYSTEM_COLUMNS_BUTTON_ID = 'edit_system_default'
    EDIT_COLUMNS_TEXT = 'Edit Columns'
    RESET_COLS_SYSTEM_DEFAULT_TEXT = 'Reset Columns to System Default'
    RESET_COLS_SYSTEM_SEARCH_DEFAULT_TEXT = 'Reset Columns to System Search Default'
    RESET_COLS_USER_DEFAULT_TEXT = 'Reset Columns to User Default'

    RESET_COLS_USER_SEARCH_DEFAULT_TEXT = 'Reset Columns to User Search Default'
    SAVE_AS_USER_DEFAULT = 'Save as User Default'
    SAVE_AS_USER_SEARCH_DEFAULT = 'Save as User Search Default ({search_name})'

    ADD_NOTES_BUTTON_TEXT = 'Add Note'
    EDIT_NOTES_TEXTBOX_CSS = '.text-input'

    TAG_MODAL_CSS = '.x-tag-modal'
    TAG_CHECKBOX_CSS = f'{TAG_MODAL_CSS} .v-list .v-input--checkbox'
    TAGS_TEXTBOX_CSS = f'{TAG_MODAL_CSS} .x-combobox_text-field--keep-open input'
    TAG_CREATE_NEW_CSS = f'{TAG_MODAL_CSS} .x-combobox_create-new-item'
    TAG_CHECKBOX_XPATH = '//div[contains(@class, \'x-tag-modal\')]//div[contains(@class, \'v-list\')]//' \
                         'div[contains(@class, \'v-list-item__title\') and text()=\'{tag_text}\']'
    TAG_PARTIAL_BASE_CSS = TAG_CHECKBOX_XPATH + '/../preceding-sibling::div' \
                                                '[contains(@class, \'v-list-item__action\')]' \
                                                '//div[contains(@class, \'v-input--checkbox\')]'
    TAG_PARTIAL_INPUT_CSS = TAG_PARTIAL_BASE_CSS + '//input'
    TAG_PARTIAL_INPUT_ICON = TAG_PARTIAL_BASE_CSS
    TAG_NEW_ITEM_XPATH = TAG_CHECKBOX_XPATH
    TAG_COMBOBOX_CSS = '.x-combobox_results-card--keep-open.v-card'

    EDIT_TAGS_BUTTON_TEXT = 'Edit Tags'
    ENTITIES_ACTIONS_DROPDOWN_CSS = '.ant-dropdown-menu'

    SAFEGUARD_MODAL_CSS = '.x-modal'
    ADAPTERS_COLUMN = '.table-td-adapters'

    COLUMN_FILTER_MODAL = '#column_filter .ant-modal'
    EXCLUDE_ADAPTER_FILTER_COMBOBOX = '.exclude-adapter__select'
    EXCLUDE_ADAPTER_FILTER_INPUT = '.ant-select-search__field'
    CLEAR_COLUMN_FILTER_MODAL = '#column_filter .clear'
    SAVE_COLUMN_FILTER_MODAL = '#column_filter .ant-btn-primary'
    COLUMN_FILTER_TERM_INCLUDE_BUTTON = '#column_filter .filter:last-child .include'
    COLUMN_FILTER_TERM_INPUT = '#column_filter .filter:last-child input'
    COLUMN_FILTER_TERM_ADD_TERM = '#column_filter .addFilter'

    EDIT_COLUMNS_MODAL_TITLE = '.x-edit-columns-modal .ant-modal-title'
    EDIT_COLUMNS_MODAL = '.x-edit-columns-modal'
    SAVE_BUTTON_TEXT = 'Save'
    EDIT_SYSTEM_DEFAULT_TITLE = 'Edit System Default'
    EDIT_SYSTEM_SEARCH_DEFAULT_HOSTNAME_TITLE = 'Edit System Search Default (Host Name)'

    SCHEDULE_TRIGGER_DROPDOWN_OPTIONS_CSS = '.x-select-content .x-select-option'
    SCHEDULE_TRIGGER_DROPDOWN_CSS = '.item_conditional .x-select .x-select-trigger'

    SAVE_QUERY_APPROVE_TEXT = 'Yes, Save'

    COLUMN_SORT_CONTAINER_CSS = '.sort-container'

    @property
    def url(self):
        raise NotImplementedError

    @property
    def root_page_css(self):
        raise NotImplementedError

    @staticmethod
    def _call_wizard_command_with_timeout(func, timeout=0.5):
        """
            Function wrapper for query wizard commands. The query wizard has debounce, thus we
            need to make sure we wait after each command to ensure the changes are rendered.
            :param f method to execute.
            :returns none
        """
        func()
        time.sleep(timeout)

    def click_query_wizard(self):
        time.sleep(0.3)
        self._call_wizard_command_with_timeout(lambda: self.driver.find_element_by_id(self.QUERY_WIZARD_ID).click())

    def select_query_field(self, text, parent=None, partial_text=True, select_num=0):
        self._call_wizard_command_with_timeout(
            lambda: self.select_option(self.QUERY_FIELD_DROPDOWN_CSS,
                                       self.DROPDOWN_TEXT_BOX_CSS,
                                       self.DROPDOWN_SELECTED_OPTION_CSS,
                                       text,
                                       parent=parent,
                                       partial_text=partial_text,
                                       select_num=select_num))

    def get_all_fields_in_field_selection(self):
        self.driver.find_element_by_css_selector(self.QUERY_FIELD_DROPDOWN_CSS).click()
        try:
            for element in self.driver.find_elements_by_css_selector('.x-select-option'):
                yield element.text
        finally:
            self.driver.find_element_by_css_selector(self.QUERY_FIELD_DROPDOWN_CSS).click()

    def get_query_field(self):
        return self.driver.find_element_by_css_selector(self.QUERY_FIELD_DROPDOWN_CSS).text

    def select_query_adapter(self, text, parent=None, select_num=0):
        self.select_option(self.QUERY_ADAPTER_DROPDOWN_CSS,
                           self.DROPDOWN_TEXT_BOX_CSS,
                           self.DROPDOWN_SELECTED_OPTION_CSS,
                           text,
                           parent=parent,
                           select_num=select_num)

    def open_query_adapters_list(self, parent=None):
        if not parent:
            parent = self.driver
        parent.find_element_by_css_selector(self.QUERY_ADAPTER_DROPDOWN_CSS).click()

    def get_query_adapters_list(self):
        self.open_query_adapters_list()
        return self.get_adapters_list()

    def open_query_adapters_list_and_open_adapter_filter(self, parent=None):
        if not parent:
            parent = self.driver
        self.open_query_adapters_list(parent)
        actions = ActionChains(self.driver)
        actions.move_to_element(parent.find_element_by_css_selector(self.FILTER_ADAPTERS_CSS))
        actions.perform()

    def click_on_filter_adapter(self, adapter, parent=None, button=False):
        self.open_query_adapters_list_and_open_adapter_filter(parent)
        filter_adapter_box = self.driver.find_element_by_css_selector(self.FILTER_ADAPTERS_BOX_CSS)
        if button:
            self.get_button(adapter, context=filter_adapter_box).click()
        else:
            self.find_element_by_text(adapter, filter_adapter_box).click()

        self._call_wizard_command_with_timeout(
            lambda: self.driver.find_element_by_css_selector(self.FILTER_ADAPTERS_CSS).click())

    def click_on_select_all_filter_adapters(self, parent=None):
        self.click_on_filter_adapter('Select all', parent, button=True)

    def click_on_clear_all_filter_adapters(self, parent=None):
        self.click_on_filter_adapter('Clear all', parent, button=True)

    def is_filtered_adapter_icon_exists(self):
        try:
            self.driver.find_element_by_css_selector(self.FILTERED_ADAPTER_ICON_CSS)
        except NoSuchElementException:
            return False
        return True

    def open_edit_columns_adapters_list(self):
        self.driver.find_element_by_css_selector(self.EDIT_COLUMNS_ADAPTER_DROPDOWN_CSS).click()

    def get_edit_columns_adapters_list(self):
        self.open_edit_columns_adapters_list()
        return self.get_adapters_list()

    def get_edit_column_adapters_dropdown_element(self):
        return self.driver.find_element_by_css_selector(self.TABLE_EDIT_COLUMN_MODAL)\
            .find_element_by_css_selector(self.EDIT_COLUMNS_ADAPTER_DROPDOWN_CSS)

    def get_edit_columns_adapters_elements(self):
        self.open_edit_columns_adapters_list()
        return self.get_edit_column_adapters_dropdown_element()\
            .find_elements_by_css_selector(self.DROPDOWN_SELECTED_OPTION_CSS)

    def get_displayed_columns_in_menu(self):
        """
        Gets all of the displayed columns that appear in the "edit column" menu
        In other words, all the fields that appear on the right side table
        """
        self.open_edit_columns()
        displayed_columns = [column.text for column in self.find_elements_by_xpath(self.DISPLAYED_COLUMNS_MENU_XPATH)]
        self.close_edit_columns()
        self.wait_for_spinner_to_end()
        self.wait_for_table_to_load()
        return displayed_columns

    def get_adapters_list(self):
        adapters_list = self.driver.find_element_by_css_selector(self.DROPDOWN_SELECTED_OPTIONS_CSS).text.split('\n')
        adapters_list.remove(self.VALUE_ADAPTERS_GENERAL)
        return adapters_list

    def get_adapters_secondary_list(self):
        adapters_list = self.driver.find_element_by_css_selector(
            self.QUERY_ADAPTER_DROPDOWN_SECONDARY_OPTIONS_CSS).text.split('\n')
        return adapters_list

    def select_query_comp_op(self, text, parent=None):
        self._call_wizard_command_with_timeout(
            lambda: self.select_option_without_search(self.QUERY_COMP_OP_DROPDOWN_CSS,
                                                      self.DROPDOWN_SELECTED_OPTION_CSS,
                                                      text,
                                                      parent=parent))

    def fill_query_wizard_date_picker(self, date_value, parent=None):
        if not parent:
            parent = self.driver
        date_picker = parent.find_element_by_css_selector(self.QUERY_DATE_PICKER_CONTAINER_CSS)
        self.fill_datepicker_date(parse_date(date_value), date_picker)
        # Sleep through the time it takes the date picker to react to the filled date
        time.sleep(0.5)

    def get_query_comp_op(self):
        return self.driver.find_element_by_css_selector(self.QUERY_COMP_OP_DROPDOWN_CSS).text

    def fill_query_string_value(self, text, parent=None):
        self._call_wizard_command_with_timeout(
            lambda: self.fill_text_field_by_css_selector(self.QUERY_VALUE_COMPONENT_INPUT_CSS,
                                                         text, context=parent))

    def fill_query_value(self, text, parent=None):
        self.fill_text_field_by_css_selector(self.QUERY_VALUE_COMPONENT_CSS, text, context=parent)

    def fill_field_comparison_query_value(self, text, parent=None):
        self._call_wizard_command_with_timeout(
            lambda: self.fill_text_field_by_css_selector(
                self.QUERY_VALUE_FIELD_COMPARISON_COMPONENT_CSS, text, context=parent))

    def select_query_value(self, text, parent=None):
        self._call_wizard_command_with_timeout(
            lambda: self.select_option(self.QUERY_VALUE_COMPONENT_CSS,
                                       self.DROPDOWN_TEXT_BOX_CSS,
                                       self.DROPDOWN_SELECTED_OPTION_CSS,
                                       text, parent=parent))

    def select_query_value_without_search(self, value, parent=None):
        self._call_wizard_command_with_timeout(
            lambda: self.select_option_without_search(self.QUERY_VALUE_COMPONENT_CSS,
                                                      self.DROPDOWN_SELECTED_OPTION_CSS,
                                                      value, parent=parent))

    def get_query_value(self, parent=None, input_type_string=False):
        css_to_use = self.QUERY_VALUE_COMPONENT_INPUT_CSS if input_type_string else self.QUERY_VALUE_COMPONENT_CSS
        if parent:
            el = parent.find_element_by_css_selector(css_to_use)
        else:
            el = self.wait_for_element_present_by_css(css_to_use)
        return el.get_attribute('value')

    def select_query_logic_op(self, text, parent=None):
        self._call_wizard_command_with_timeout(
            lambda: self.select_option_without_search(self.QUERY_LOGIC_DROPDOWN_CSS,
                                                      self.DROPDOWN_SELECTED_OPTION_CSS, text,
                                                      parent=parent))

    def click_wizard_outdated_toggle(self):
        self.driver.find_element_by_css_selector(self.OUTDATED_TOGGLE_CSS).click()

    def click_search(self):
        self.click_button('Search', call_space=False)

    def get_search_button(self):
        return self.get_button('Search')

    def find_first_id(self):
        return self.driver.find_element_by_css_selector(self.TABLE_FIRST_ROW_CSS).get_attribute('id')

    def click_row(self) -> str:
        """
        Click on the first entity in the table
        :return: the internal_axon_id of the axonius entity
        """
        row_data = self.driver.find_element_by_css_selector(self.TABLE_FIRST_ROW_DATA_CSS)
        ActionChains(self.driver).move_to_element_with_offset(row_data, 4, 4).click().perform()
        self.wait_for_spinner_to_end()
        return self.driver.current_url.split('/')[-1]

    def find_query_search_input(self):
        return self.driver.find_element_by_css_selector(self.QUERY_SEARCH_INPUT_CSS)

    def get_query_search_input_value(self):
        return self.driver.find_element_by_css_selector(self.QUERY_SEARCH_INPUT_CSS).get_attribute('value')

    def get_query_search_input_attribute(self, attribute):
        return self.find_query_search_input().get_attribute(attribute)

    def fill_filter(self, filter_string):
        self.fill_text_field_by_css_selector(self.QUERY_SEARCH_INPUT_CSS, filter_string)

    def enter_search(self):
        self.key_down_enter(self.find_query_search_input())
        self.wait_for_spinner_to_end()

    def open_search_list(self):
        self.key_down_arrow_down(self.find_query_search_input())

    def check_search_list_for_names(self, query_names):
        self.open_search_list()
        for name in query_names:
            assert self.driver.find_element_by_xpath(self.QUERY_SEARCH_DROPDOWN_XPATH.format(query_name_text=name))
        self.close_dropdown()

    def check_search_list_for_absent_names(self, query_names):
        self.open_search_list()
        for name in query_names:
            assert len(self.driver.find_elements_by_xpath(
                self.QUERY_SEARCH_DROPDOWN_XPATH.format(query_name_text=name))) == 0
        self.close_dropdown()

    @retry(wait_fixed=500, stop_max_attempt_number=30)
    def select_query_by_name(self, query_name):
        el = self.wait_for_element_present_by_xpath(self.QUERY_SEARCH_DROPDOWN_XPATH.format(query_name_text=query_name))
        el.click()

    @retry(wait_fixed=500, stop_max_attempt_number=10)
    def select_search_everywhere(self):
        el = self.wait_for_element_present_by_css(self.QUERY_SEARCH_EVERYWHERE_CSS)
        el.click()

    def find_search_value(self):
        return self.find_query_search_input().get_attribute('value')

    def get_raw_count_entities(self, table_count_css=TABLE_COUNT_CSS) -> str:
        return self.driver.find_element_by_css_selector(table_count_css).text

    def count_entities(self, table_count_css=TABLE_COUNT_CSS):
        """
        How many entities are in the current table?
        :return:
        """
        time.sleep(2)
        wait_until(lambda: 'Loading' not in self.get_raw_count_entities(table_count_css))
        match_count = re.search(r'\((\d+)\)', self.get_raw_count_entities(table_count_css))
        assert match_count and len(match_count.groups()) == 1
        return int(match_count.group(1))

    def count_selected_entities(self):
        wait_until(lambda: 'selected' in self.driver.find_element_by_css_selector(self.TABLE_SELECTED_COUNT_CSS).text)
        match_count = re.search(r'\[ (.+) selected',
                                self.driver.find_element_by_css_selector(self.TABLE_SELECTED_COUNT_CSS).text)
        assert match_count and len(match_count.groups()) == 1
        return int(match_count.group(1))

    def verify_no_entities_selected(self):
        return self.wait_for_element_absent_by_css(self.TABLE_SELECTED_COUNT_CSS) is None

    def click_select_all_entities(self):
        self.click_select_all_label('Select all')

    def click_select_all_label(self, text):
        element = self.driver.find_element_by_css_selector(self.TABLE_SELECT_ALL_BUTTON_CSS)
        if element.text == text:
            self.driver.find_element_by_css_selector(self.TABLE_SELECT_ALL_BUTTON_CSS).click()

    def click_clear_all_entities(self):
        self.click_select_all_label('Clear all')

    def add_query_expression(self):
        self._call_wizard_command_with_timeout(
            lambda: self.driver.find_element_by_css_selector(self.QUERY_ADD_EXPRESSION_CSS).click())

    def toggle_left_bracket(self, expression_element):
        expression_element.find_element_by_css_selector(self.QUERY_BRACKET_LEFT_CSS).click()

    def toggle_right_bracket(self, expression_element):
        expression_element.find_element_by_css_selector(self.QUERY_BRACKET_RIGHT_CSS).click()

    def toggle_not(self, expression_element=None):
        if not expression_element:
            expression_element = self.driver
        self._call_wizard_command_with_timeout(
            lambda: expression_element.find_element_by_css_selector(self.QUERY_NOT_CSS).click())

    def select_context_all(self, expression_element):
        self.select_option_without_search(self.QUERY_CONTEXT_CSS,
                                          self.DROPDOWN_SELECTED_OPTION_CSS,
                                          'Aggregated Data',
                                          parent=expression_element)

    def select_context_obj(self, expression_element):
        self.select_option_without_search(self.QUERY_CONTEXT_CSS,
                                          self.DROPDOWN_SELECTED_OPTION_CSS,
                                          'Complex Field',
                                          parent=expression_element)

    def select_context_ent(self, expression_element):
        self.select_option_without_search(self.QUERY_CONTEXT_CSS,
                                          self.DROPDOWN_SELECTED_OPTION_CSS,
                                          'Asset Entity',
                                          parent=expression_element)

    def select_context_cmp(self, expression_element):
        self.select_option_without_search(self.QUERY_CONTEXT_CSS,
                                          self.DROPDOWN_SELECTED_OPTION_CSS,
                                          'Field Comparison',
                                          parent=expression_element)

    def select_asset_entity_adapter(self, expression_element, adapter_title):
        self._call_wizard_command_with_timeout(
            lambda: self.select_option(self.QUERY_ASSET_ENTITY_ADAPTER_CSS,
                                       self.DROPDOWN_TEXT_BOX_CSS,
                                       self.DROPDOWN_SELECTED_OPTION_CSS,
                                       adapter_title,
                                       parent=expression_element))

    def get_asset_entity_children(self, expression_element):
        if not expression_element:
            expression_element = self.driver
        return expression_element.find_elements_by_css_selector(self.QUERY_ASSET_ENTITY_CHILDREN_CSS)

    def get_asset_entity_children_first(self):
        return self.get_asset_entity_children(self.find_expressions()[0])

    def select_asset_entity_field(self, child_element, field_title):
        self._call_wizard_command_with_timeout(
            lambda: self.select_option(self.QUERY_ASSET_ENTITY_FIELD_CSS,
                                       self.DROPDOWN_TEXT_BOX_CSS,
                                       self.DROPDOWN_SELECTED_OPTION_CSS,
                                       field_title,
                                       parent=child_element))

    def remove_query_expression(self, expression_element):
        expression_element.find_element_by_css_selector(self.QUERY_REMOVE_EXPRESSION_CSS).click()

    def clear_query_wizard(self):
        self._call_wizard_command_with_timeout(lambda: self.click_button('Clear'))

    def clear_filter(self):
        # Explicit clear needed for Mac - 'fill_filter' will not replace the text
        self.click_query_wizard()
        self.clear_query_wizard()
        self.close_dropdown()
        self.wait_for_table_to_load()

    def find_expressions(self):
        return self.driver.find_elements_by_css_selector(self.QUERY_EXPRESSIONS_CSS)

    def find_conditions(self, parent=None):
        if not parent:
            parent = self.driver
        return parent.find_elements_by_css_selector(self.QUERY_CONDITIONS_CSS)

    def add_query_child_condition(self, parent=None):
        if not parent:
            parent = self.driver
        parent.find_element_by_css_selector(self.QUERY_NEST_EXPRESSION_CSS).click()

    def build_query_active_directory(self):
        self.click_query_wizard()
        self.select_query_adapter(AD_ADAPTER_NAME)
        self.wait_for_table_to_load()
        self.close_dropdown()

    def build_query_field_contains(self, field_name, field_value):
        self.build_query(field_name, field_value, COMP_CONTAINS)

    def build_query_field_regex(self, field_name, field_value):
        self.build_query(field_name, field_value, COMP_REGEX)

    def build_query_field_contains_with_adapter(self, field_name, field_value, adapter_name):
        self.build_query_with_adapter(field_name, field_value, COMP_CONTAINS, adapter_name)

    def build_query(self, field_name, field_value, comp_op):
        self.click_query_wizard()
        self.select_query_field(field_name)
        self.select_query_comp_op(comp_op)
        if field_value:
            self.fill_query_string_value(field_value)
        self.wait_for_table_to_load()
        self.close_dropdown()

    def build_query_with_adapter(self, field_name, field_value, comp_op, adapter_name):
        self.click_query_wizard()
        self.select_query_adapter(adapter_name)
        self.select_query_field(field_name, partial_text=False)
        self.select_query_comp_op(comp_op)
        self.fill_query_string_value(field_value)
        self.wait_for_table_to_load()
        self.close_dropdown()

    def build_asset_entity_query(self, adapter_name, field_name_1, value_string_1, field_name_2, value_string_2):
        """
        Use Query Wizard to create a query on Asset Entity context
        Fetched data will match given given fields and values, with in given Adapters' entities (device / user)
        """
        self.switch_to_page()
        self.click_query_wizard()
        expression = self.find_expressions()[0]
        self.select_context_ent(expression)
        self.select_asset_entity_adapter(expression, adapter_name)
        self.add_query_child_condition(expression)
        children = self.get_asset_entity_children(expression)
        self.select_asset_entity_field(children[0], field_name_1)
        self.select_query_comp_op(COMP_EQUALS, children[0])
        self.fill_query_string_value(value_string_1, children[0])
        self.select_asset_entity_field(children[1], field_name_2)
        self.select_query_comp_op(COMP_EQUALS, children[1])
        self.fill_query_string_value(value_string_2, children[1])

    def change_asset_entity_query(self, child_element, field_name=None, value_string=None):
        """
        Assumes Query Wizard is open with some Asset Entity query
        Change the field / value of given child condition to those given
        """
        if field_name:
            self.select_asset_entity_field(child_element, field_name)
        if value_string:
            self.fill_query_string_value(value_string, child_element)

    def change_query_params(self, field, value, comp_op, field_type, subfield=None):
        """
        Assumes Query Wizard is open and contains one built query
        Change the field, operator and value to those given
        """
        expressions = self.find_expressions()
        assert len(expressions) == 1
        if subfield:
            self.select_context_obj(expressions[0])
        self.select_query_field(field, expressions[0])
        conditions = self.find_conditions()
        if len(conditions) == 1 and subfield:
            self.select_query_field(subfield, conditions[0])
        self.select_query_comp_op(comp_op, expressions[0])
        if field_type == 'string':
            self.select_query_value(value, expressions[0])
        elif field_type == 'integer':
            self.select_query_value_without_search(value, expressions[0])

    def find_rows_with_data(self):
        return self.driver.find_elements_by_xpath(self.TABLE_DATA_ROWS_XPATH)

    def select_page_size(self, page_size):
        self.driver.find_element_by_xpath(self.TABLE_PAGE_SIZE_XPATH.format(page_size_text=page_size)).click()

    def select_pagination_index(self, link_order):
        self.driver.find_elements_by_xpath(self.TABLE_PAGE_SELECT_XPATH)[link_order - 1].click()

    def find_active_page_number(self):
        return self.driver.find_element_by_xpath(self.TABLE_PAGE_ACTIVE_XPATH).text

    def click_sort_column(self, col_name):
        header = self.driver.find_element_by_xpath(self.TABLE_HEADER_BY_NAME_XPATH.format(col_name_text=col_name))
        ActionChains(self.driver).move_to_element(header).perform()
        header.find_element_by_css_selector(self.COLUMN_SORT_CONTAINER_CSS).click()

    def check_sort_column(self, col_name, desc=True):
        header = self.driver.find_element_by_xpath(self.TABLE_HEADER_BY_NAME_XPATH.format(col_name_text=col_name))
        sort = header.find_element_by_css_selector('.sort')
        assert sort.get_attribute('class') == ('sort down' if desc else 'sort up')

    def open_column_filter_modal(self, col_name):
        header = self.driver.find_element_by_xpath(self.TABLE_HEADER_BY_NAME_XPATH.format(col_name_text=col_name))
        ActionChains(self.driver).move_to_element(header).perform()
        header.find_element_by_css_selector('.filter').click()
        self.wait_for_element_present_by_css(self.COLUMN_FILTER_MODAL)
        # wait for modal animation to end
        time.sleep(0.5)

    def toggle_exclude_adapters_combobox(self, displayed=True):
        self.driver.find_element_by_css_selector(self.EXCLUDE_ADAPTER_FILTER_COMBOBOX).click()
        wait_until(lambda:
                   self.driver.find_element_by_css_selector(self.ANT_SELECT_MENU_ITEM_CSS).is_displayed() == displayed)

    def clear_column_filter_modal(self):
        self.driver.find_element_by_css_selector(self.CLEAR_COLUMN_FILTER_MODAL).click()

    def save_column_filter_modal(self):
        self.driver.find_element_by_css_selector(self.SAVE_COLUMN_FILTER_MODAL).click()
        self.wait_for_table_to_be_responsive()

    def add_filter_column_filter_modal(self):
        self.driver.find_element_by_css_selector(self.COLUMN_FILTER_TERM_ADD_TERM).click()

    def fill_filter_column_filter_modal(self, filter_obj):
        if not filter_obj.get('include', True):
            self.driver.find_element_by_css_selector(self.COLUMN_FILTER_TERM_INCLUDE_BUTTON).click()
        self.fill_text_field_by_css_selector(self.COLUMN_FILTER_TERM_INPUT, filter_obj.get('term', ''))

    def add_exclude_adapters_combobox(self, text):
        self.fill_text_field_by_css_selector(self.EXCLUDE_ADAPTER_FILTER_INPUT, text)
        self.driver.find_element_by_css_selector(self.ANT_SELECT_MENU_ITEM_CSS).click()

    def filter_column(self, col_name: str = '', filter_list: list = None, adapter_list: list = None):
        self.open_column_filter_modal(col_name)
        self.clear_column_filter_modal()
        if filter_list:
            for index, filter_dict in enumerate(filter_list):
                if index > 1:
                    self.add_filter_column_filter_modal()
                self.fill_filter_column_filter_modal(filter_dict)
        if adapter_list:
            self.toggle_exclude_adapters_combobox(displayed=True)
            for adapter in adapter_list:
                self.add_exclude_adapters_combobox(adapter)
            self.toggle_exclude_adapters_combobox(displayed=False)
        self.save_column_filter_modal()

    def get_field_columns_header_text(self):
        headers = self.driver.find_element_by_xpath(self.TABLE_HEADER_FIELD_XPATH)
        header_columns = headers.find_elements_by_css_selector(self.TABLE_HEADER_CELLS_CSS)
        return [self._get_column_title(head) for head in header_columns if self._get_column_title(head)]

    def get_note_by_text(self, note_text):
        return self.driver.find_element_by_xpath(self.NOTES_SEARCH_BY_TEXT_XPATH.format(note_text=note_text))

    def get_notes_column_data(self, col_name):
        parent = self.driver.find_element_by_css_selector(self.NOTES_CONTENT_CSS)
        return self.get_column_data_inline(col_name, parent)

    def get_column_data_with_remainder(self, data_section_xpath, col_name, parent=None, generic_col=True,
                                       merge_cells=True):
        if not parent:
            parent = self.driver
        col_position = self.count_sort_column(col_name, parent) \
            if generic_col else self.count_specific_column(col_name, parent)
        values = []
        for index, el in \
                enumerate(parent.find_elements_by_xpath(data_section_xpath.format(data_position=col_position)),
                          start=1):
            column_type = ''
            slice_elements = el.find_elements_by_css_selector('.x-slice')
            if len(slice_elements) == 1:
                column_type = slice_elements[0].find_element_by_tag_name('div').get_attribute('class')
            remainder_values = None
            if 'array' in column_type:
                remainder_values = self.get_field_values_with_remainder(col_position, el, index)
            if remainder_values:
                if merge_cells:
                    for value in remainder_values:
                        values.append(value)
                else:
                    values.append(remainder_values)
            elif el.text.strip():
                values.append(el.text.strip())
        return values

    def get_field_values_with_remainder(self, col_position: int, element: object, index: int):
        try:
            # try to get all values from hovering on the value (works only if there is a tooltip)
            remainder_count = self.hover_remainder(index, col_position)
            if remainder_count:
                field_values = [element.text for element in self.get_tooltip_table_data()]
            else:
                field_values = self.get_field_values(element)
        except NoSuchElementException:
            field_values = self.get_field_values(element)
        return field_values

    def get_field_values(self, element: WebElement):
        # if the cell contains images then get the title of the images - else get the text values of the cell
        images = element.find_elements_by_css_selector('img')
        if images:
            field_values = self.get_hover_images_texts(element)
        else:
            field_values = [el.text.strip() if el.text else None for index, el
                            in enumerate(element.find_elements_by_css_selector('.item'))]
        return field_values

    def get_column_data_inline_with_remainder(self, col_name, parent=None):
        return self.get_column_data_with_remainder(self.TABLE_DATA_INLINE_XPATH, col_name, parent)

    def get_column_cells_data_inline_with_remainder(self, col_name, parent=None):
        return self.get_column_data_with_remainder(self.TABLE_DATA_INLINE_XPATH, col_name, parent, merge_cells=False)

    def get_column_data_slicer(self, col_name, parent=None, generic_col=True):
        return self.get_column_data(self.TABLE_DATA_SLICER_XPATH, col_name, parent, generic_col)

    def get_column_data_expand_row(self, col_name, parent=None):
        return self.get_column_data(self.TABLE_DATA_EXPAND_ROW_XPATH, col_name, parent)

    def find_data_expand_row(self):
        return self.find_element_by_xpath(self.TABLE_DATA_EXPAND_ROW_XPATH)

    def get_column_data_expand_cell(self, col_name, parent=None):
        return self.get_column_data(self.TABLE_DATA_EXPAND_CELL_BODY_XPATH, col_name, parent)

    def get_expand_cell_column_data(self, col_name, expanded_col_name):
        col_position = self.count_sort_column(col_name)
        return self.get_column_data('.//td[position()={data_position}]',
                                    expanded_col_name,
                                    self.driver.find_element_by_xpath(self.TABLE_DATA_EXPAND_CELL_XPATH.format(
                                        data_position=col_position)))

    def get_column_data_adapter_names(self, parent=None):
        return self.get_column_data_adapter_attribute(parent=parent, attribute='alt')

    def get_column_data_adapter_title_tooltip(self):
        return self.get_column_data_adapter_attribute(attribute='title')

    def get_column_data_adapter_attribute(self, parent=None, attribute=None):
        if not parent:
            parent = self.driver
        return [el.get_attribute(attribute) for el in parent.find_elements_by_xpath(self.TABLE_DATA_IMG_XPATH)
                if el.get_attribute(attribute)]

    def get_field_table_data_with_ids(self):
        return [[data_cell.text for data_cell in data_row.find_elements_by_tag_name('td')]
                for data_row in self.find_elements_by_xpath(self.TABLE_FIELD_ROWS_XPATH_WITH_IDS)]

    def get_all_custom_data(self):
        return [data.text for data in self.find_elements_by_xpath(self.TABLE_SCHEMA_CUSTOM)]

    def toggle_select_all_rows_checkbox(self):
        self.driver.find_element_by_css_selector(self.TABLE_SELECT_ALL_CURRENT_PAGE_CHECKBOX_CSS).click()

    # retrying because sometimes the table hasn't fully loaded
    @retry(wait_fixed=20, stop_max_delay=3000)
    def get_all_data_proper(self):
        """
        Returns a list of dict where each dict is a dict between a field name (i.e. adapter, asset_name) and
        the respective value
        """
        result = []
        column_names = [self._get_column_title(x)
                        for x in self.driver.find_elements_by_css_selector(self.TABLE_HEADER_CELLS_CSS)
                        if self._get_column_title(x)]
        all_entities = self.driver.find_elements_by_css_selector(self.ALL_ENTITIES_CSS)
        for entity in all_entities:
            if not entity.text.strip():
                # an empty row represents the end
                break

            fields_values = entity.find_elements_by_tag_name('td')[2:]
            assert len(fields_values) == len(column_names), 'nonmatching fields'
            fields_values = [x.find_element_by_css_selector(self.TABLE_DATA_ROWS_TEXT_CSS) for x in fields_values]
            fields_values = [x.get_attribute('title') or x.text for x in fields_values]
            result.append({
                field_name: field_value
                for field_name, field_value in zip(column_names, fields_values)
                if field_name
            })
        return result

    def is_text_in_coloumn(self, col_name, text):
        return any(text in item for item in self.get_column_data_slicer(col_name))

    def find_table_option_by_title(self, option_title):
        return self.driver.find_element_by_xpath(self.TABLE_OPTIONS_ITEM_XPATH.format(option_title=option_title))

    def open_edit_columns(self, system_default=False):
        self.open_columns_menu()
        self.driver.find_element_by_id(
            self.EDIT_SYSTEM_COLUMNS_BUTTON_ID if system_default else self.EDIT_USER_COLUMN_BUTTON_ID
        ).click()
        self.wait_for_element_present_by_css(self.EDIT_COLUMNS_MODAL)
        # wait for modal open animation to end
        time.sleep(0.5)

    def select_column_adapter(self, adapter_title):
        self.select_option(self.EDIT_COLUMNS_ADAPTER_DROPDOWN_CSS,
                           self.DROPDOWN_TEXT_BOX_CSS,
                           self.DROPDOWN_SELECTED_OPTION_CSS,
                           adapter_title)

    def get_edit_columns_modal_title(self):
        return self.driver.find_element_by_css_selector(self.EDIT_COLUMNS_MODAL_TITLE).text

    def close_edit_columns(self):
        self.click_button('Done')

    def close_edit_columns_save_user_default(self, specific_search_name=''):
        if specific_search_name:
            self.click_button(
                self.SAVE_AS_USER_SEARCH_DEFAULT.format(search_name=specific_search_name))
        else:
            self.click_button(self.SAVE_AS_USER_DEFAULT)

    def close_edit_columns_save_system_default(self):
        edit_columns_modal = self.driver.find_element_by_css_selector(self.EDIT_COLUMNS_MODAL)
        self.get_button(self.SAVE_BUTTON_TEXT, context=edit_columns_modal).click()

        modal_confirm = self.driver.find_element_by_css_selector(self.MODAL_CONFIRM)
        self.click_ant_button(self.SAVE_BUTTON_TEXT, context=modal_confirm)

        self.wait_for_element_absent_by_css(self.ANTD_MODAL_OVERLAY_CSS)

    def close_edit_columns_cancel_system_default(self):
        edit_columns_modal = self.driver.find_element_by_css_selector(self.EDIT_COLUMNS_MODAL)
        self.get_button(self.SAVE_BUTTON_TEXT, context=edit_columns_modal).click()

        modal_confirm = self.driver.find_element_by_css_selector(self.MODAL_CONFIRM)
        self.click_ant_button(self.CANCEL_BUTTON, context=modal_confirm)
        self.wait_for_element_absent_by_css(self.MODAL_CONFIRM)

        self.get_button(self.CANCEL_BUTTON, context=edit_columns_modal).click()

        self.wait_for_element_absent_by_css(self.ANTD_MODAL_OVERLAY_CSS)

    def edit_columns(self, add_col_names: list = None, remove_col_names: list = None, adapter_title: str = None):
        self.open_edit_columns()
        if adapter_title:
            self.select_column_adapter(adapter_title)
        if add_col_names:
            self.add_columns(add_col_names)
        if remove_col_names:
            self.remove_columns(remove_col_names)
        self.close_edit_columns()
        self.wait_for_spinner_to_end()
        self.wait_for_table_to_load()

    def add_columns(self, col_names, adapter_title: str = None):
        if adapter_title:
            self.select_column_adapter(adapter_title)
        for col_name in col_names:
            self.select_column_available(col_name)
        self.click_button('Add >>')

    def remove_columns(self, col_names, adapter_title: str = None):
        if adapter_title:
            self.select_column_adapter(adapter_title)
        for col_name in col_names:
            self.select_column_displayed(col_name)
        self.click_button('<< Remove')

    def select_column_available(self, col_title):
        self.select_column('stock', col_title)

    def select_column_displayed(self, col_title):
        self.select_column('view', col_title)

    def select_column(self, col_type, col_title):
        self.fill_text_field_by_css_selector(f'.{col_type} .x-search-input .input-value', col_title)
        self.driver.find_element_by_xpath(
            self.EDIT_COLUMNS_SELECT_XPATH.format(list_type=col_type, col_title=col_title)).click()

    def reset_columns_system_default(self):
        self.open_columns_menu()
        self.driver.find_element_by_id(self.RESET_COLS_SYSTEM_BUTTON_ID).click()

    def reset_columns_user_default(self):
        self.open_columns_menu()
        self.driver.find_element_by_id(self.RESET_COLS_USER_BUTTON_ID).click()

    def is_query_error(self, text=None):
        if not text:
            self.wait_for_element_absent_by_css(self.QUERY_ERROR_CSS)
            return True
        return text == self.wait_for_element_present_by_css(self.QUERY_ERROR_CSS).text

    def click_save_query(self):
        wait_until(lambda: not self.is_query_save_as_disabled())
        self.driver.find_element_by_id(self.SAVE_QUERY_ID).click()

    def is_query_save_as_disabled(self):
        return self.is_element_disabled(self.get_button(self.SAVE_AS_BUTTON))

    def is_query_save_disabled(self):
        el = self.driver.find_element_by_id(self.SAVE_AS_DROPDOWN_SAVE_CHANGES_ID)
        return el.get_attribute('aria-disabled') == 'true'

    def fill_query_name(self, name):
        self.fill_text_field_by_css_selector(self.SAVE_QUERY_NAME_SELECTOR, name)

    def set_query_private(self):
        self.driver.find_element_by_id(self.SAVE_QUERY_PRIVATE_CHECKBOX_ID).click()

    def fill_query_description(self, description):
        self.fill_text_field_by_css_selector(self.SAVE_QUERY_DESCRIPTION_SELECTOR, description)

    def click_actions_tag_button(self):
        self.driver.find_element_by_id(self.TABLE_ACTIONS_TAG).click()

    def click_actions_enforce_button(self, enforcement_button_id):
        actions = ActionChains(self.driver)
        actions.move_to_element(self.driver.find_element_by_id(self.TABLE_ACTIONS_ENFORCE_SUB_MENU)).perform()
        self.driver.find_element_by_id(enforcement_button_id).click()

    def is_enforce_button_disabled(self, enforcement_button_id):
        actions = ActionChains(self.driver)
        actions.move_to_element(self.driver.find_element_by_id(self.TABLE_ACTIONS_ENFORCE_SUB_MENU)).perform()
        return self.is_element_has_disabled_class(
            self.driver.find_element_by_id(enforcement_button_id))

    def open_edit_tags(self):
        self.click_button(self.EDIT_TAGS_BUTTON_TEXT)

    def get_edit_tags_button(self):
        return self.get_enabled_button(self.EDIT_TAGS_BUTTON_TEXT)

    def get_remove_tags_button(self):
        return self.get_enabled_button(self.REMOVE_BUTTON)

    def assert_edit_tags_disabled(self):
        self.wait_for_element_present_by_xpath(
            self.DISABLED_BUTTON_XPATH.format(button_text=self.EDIT_TAGS_BUTTON_TEXT))

    def assert_remove_tags_disabled(self):
        self.wait_for_element_present_by_xpath(
            self.DISABLED_BUTTON_XPATH.format(button_text=self.REMOVE_BUTTON))

    def click_save_query_cancel_button(self):
        context_element = self.wait_for_element_present_by_css('.save-query-dialog')
        self.click_button(text='Cancel', context=context_element)
        self.wait_for_element_absent_by_css(self.QUERY_MODAL_OVERLAY)

    def click_save_query_save_button(self, query_name=None):
        context_element = self.wait_for_element_present_by_css('.save-query-dialog')
        self.click_button(text='Save', context=context_element)
        self.wait_for_element_absent_by_css(self.QUERY_MODAL_OVERLAY)

    def reset_query(self):
        self.click_button('Reset')

    def open_actions_query(self):
        el = self.driver.find_element_by_css_selector(self.SAVE_AS_DROPDOWN_ARROW)
        el.click()

    def discard_changes_query(self):
        self.open_actions_query()
        el = self.driver.find_element_by_id(self.SAVE_AS_DROPDOWN_DISCARD_ID)
        el.click()
        self.wait_for_table_to_load()

    def save_query(self, query_name):
        wait_until(lambda: not self.is_query_save_as_disabled())
        self.click_save_query()
        self.fill_query_name(query_name)
        self.click_save_query_save_button(query_name=query_name)

    def save_query_as(self, query_name, is_private: bool = False):
        wait_until(lambda: not self.is_query_save_as_disabled())
        self.click_button(self.SAVE_AS_BUTTON)
        self.fill_query_name(query_name)
        if is_private:
            self.set_query_private()
        self.click_save_query_save_button()

    def save_existing_query(self):
        self.open_actions_query()
        el = self.driver.find_element_by_id(self.SAVE_AS_DROPDOWN_SAVE_CHANGES_ID)
        el.click()
        self.safeguard_click_confirm(self.SAVE_QUERY_APPROVE_TEXT)

    def create_private_query(self, query_name):
        self.switch_to_page()
        self.wait_for_table_to_be_responsive()
        self.fill_filter(self.RANDOM_FILTER_VALUE)
        self.enter_search()
        self.save_query_as(query_name, is_private=True)

    def assert_private_query_checkbox_hidden(self, query_name):
        self.click_button(query_name)
        self.assert_element_absent_by_id(self.SAVE_QUERY_PRIVATE_CHECKBOX_ID)
        self.click_save_query_cancel_button()

    def assert_private_query_checkbox_is_disabled(self, query_name):
        self.click_button(query_name)
        assert self.is_element_disabled(self.driver.find_element_by_id(self.SAVE_QUERY_PRIVATE_CHECKBOX_ID))
        self.click_save_query_cancel_button()

    def rename_query(self, query_name, new_query_name):
        self.click_button(query_name)
        self.fill_query_name(new_query_name)
        self.click_save_query_save_button()

    def run_filter_and_save(self,
                            query_name,
                            query_filter,
                            optional_sort: str = None,
                            optional_reset_before: bool = True):
        if optional_reset_before:
            self.reset_query()
        self.fill_filter(query_filter)
        self.enter_search()
        self.wait_for_table_to_load()
        if optional_sort:
            self.click_sort_column(optional_sort)
            self.wait_for_table_to_load()
        self.save_query(query_name)

    def customize_view_and_save(self, query_name, page_size, sort_field, add_columns, remove_columns, query_filter):
        self.select_page_size(page_size)
        self.wait_for_table_to_load()
        self.click_sort_column(sort_field)
        self.wait_for_table_to_load()
        self.edit_columns(add_columns, remove_columns)
        self.wait_for_table_to_load()
        self.run_filter_and_save(query_name, query_filter, None, False)

    def execute_saved_query(self, query_name):
        self.fill_filter(query_name)
        self.open_search_list()
        self.select_query_by_name(query_name)
        self.wait_for_table_to_load()

    def remove_selected(self):
        self.click_button(self.DELETE_BUTTON)

    def approve_remove_selected(self):
        modals = self.driver.find_elements_by_css_selector(self.SAFEGUARD_MODAL_CSS)
        self.logger.info(f'number of {self.SAFEGUARD_MODAL_CSS} in approve_remove_selected is: {len(modals)}')
        safeguard_modal = self.driver.find_element_by_css_selector(self.SAFEGUARD_MODAL_CSS)
        self.click_button(self.DELETE_BUTTON, context=safeguard_modal)
        self.wait_for_element_absent_by_css(self.SAFEGUARD_MODAL_CSS)

    def click_enforcement_tasks_tab(self):
        self.click_tab(self.ENFORCEMENT_DATA_TAB_TITLE)

    def click_extended_data_tasks_tab(self):
        self.click_tab(self.EXTENDED_DATA_TAB_TITLE)

    def click_general_tab(self):
        self.click_tab(self.GENERAL_DATA_TAB_TITLE)

    def click_adapters_tab(self):
        self.click_tab(self.ADAPTERS_DATA_TAB_TITLE)

    def click_notes_tab(self):
        self.driver.find_element_by_css_selector(self.NOTES_TAB_CSS).click()

    def click_tags_tab(self):
        self.driver.find_element_by_css_selector(self.TAGS_TAB_CSS).click()

    def click_custom_data_tab(self):
        self.driver.find_element_by_css_selector(self.CUSTOM_DATA_TAB_CSS).click()

    def fill_save_note(self, note_text, toast_text):
        self.fill_text_field_by_css_selector(self.EDIT_NOTES_TEXTBOX_CSS, note_text)
        self.click_button(self.SAVE_BUTTON)
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS)
        self.wait_for_toaster(toast_text)

    def create_note(self, note_text):
        self.click_button(self.ADD_NOTES_BUTTON_TEXT)
        self.fill_save_note(note_text, self.NOTES_CREATED_TOASTER)

    def get_add_note_button(self):
        return self.get_enabled_button(self.ADD_NOTES_BUTTON_TEXT)

    def assert_add_note_disabled(self):
        self.wait_for_element_present_by_xpath(
            self.DISABLED_BUTTON_XPATH.format(button_text=self.ADD_NOTES_BUTTON_TEXT))

    def edit_note(self, note_text):
        self.click_row()
        self.fill_save_note(note_text, self.NOTES_EDITED_TOASTER)

    def can_edit_notes(self):
        return len(self.driver.find_elements_by_css_selector(self.TABLE_FIRST_ROW_DATA_CSS)) > 0

    def remove_note(self):
        self.click_row_checkbox()
        self.remove_selected()
        self.approve_remove_selected()
        self.wait_for_element_absent_by_id(self.SAFEGUARD_APPROVE_BUTTON_ID)

    def find_notes_row_readonly(self):
        parent = self.driver.find_element_by_css_selector(self.NOTES_CONTENT_CSS)
        return self.find_row_readonly(parent)

    def find_row_readonly(self, parent=None):
        if not parent:
            parent = self.driver
        return parent.find_elements_by_css_selector('.x-table-row:not(.clickable)')

    def search_note(self, search_text):
        self.fill_text_field_by_css_selector(self.NOTES_SEARCH_INUPUT_CSS, search_text)

    def close_csv_config_dialog(self):
        self.get_cancel_button(self.driver.find_element_by_id(self.EXPORT_CSV_CONFIG_MODAL_ID)).click()
        self.wait_for_csv_config_dialog_to_be_absent()

    def confirm_csv_config_dialog(self):
        self.get_export_button(self.driver.find_element_by_id(self.EXPORT_CSV_CONFIG_MODAL_ID)).click()
        self.wait_for_csv_config_dialog_to_be_absent()

    def get_export_button(self, context=None):
        return self.get_button('Export', context=context)

    def wait_for_csv_config_dialog_to_be_absent(self):
        self.wait_for_element_absent_by_id(self.EXPORT_CSV_CONFIG_MODAL_ID)

    def get_csv_delimiter_field(self):
        return self.driver.find_element_by_id(self.EXPORT_CSV_DELIMITER_ID).get_attribute('value')

    def get_csv_max_rows_field(self):
        return int(self.driver.find_element_by_id(self.EXPORT_CSV_MAX_ROWS_ID).get_attribute('value'))

    def set_csv_delimiter_field(self, delimiter):
        self.fill_text_field_by_element_id(self.EXPORT_CSV_DELIMITER_ID, delimiter)

    def set_csv_max_rows_field(self, max_rows):
        self.fill_text_field_by_element_id(self.EXPORT_CSV_MAX_ROWS_ID, max_rows)

    def is_csv_config_matching_default_fields(self):
        # Little hack to fix delimiter format
        delimiter = self.get_csv_delimiter_field().replace('\\n', '\n')
        return delimiter == CELL_JOIN_DEFAULT and self.get_csv_max_rows_field() == MAX_ROWS_LEN

    def click_export_csv(self, wait_for_config_modal=True):
        self.click_button(self.EXPORT_CSV_BUTTON_TEXT)
        if wait_for_config_modal:
            self.wait_for_element_present_by_id(self.EXPORT_CSV_CONFIG_MODAL_ID)
            time.sleep(0.1)  # wait for modal to open

    def open_export_csv(self):
        self.click_export_csv()
        self.wait_for_element_present_by_id(self.EXPORT_CSV_CONFIG_MODAL_ID)
        time.sleep(0.1)  # wait for modal to open

    def wait_for_export_csv_button_visible(self):
        self.wait_for_element_present_by_text(self.EXPORT_CSV_BUTTON_TEXT, retries=600 * 5)

    def click_device_enforcement_task_export_csv(self):
        self.click_export_csv(False)
        self.wait_for_export_csv_button_visible()

    def get_csrf_token(self) -> str:
        session = requests.Session()
        cookies = self.driver.get_cookies()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])
        resp = session.get('https://127.0.0.1/api/csrf')
        csrf_token = resp.text
        resp.close()
        return csrf_token

    def generate_csv(self, entity_type, fields: list, filters=None, excluded_adapters: list = None,
                     field_filters: list = None, delimiter: str = None, max_rows: int = None):
        session = requests.Session()
        cookies = self.driver.get_cookies()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])
        session.headers['X-CSRF-Token'] = self.get_csrf_token()
        logger.info('posting for csv')
        result = session.post(f'https://127.0.0.1/api/{entity_type}/csv',
                              json={'fields': fields,
                                    'filter': filters,
                                    'excluded_adapters': excluded_adapters,
                                    'field_filters': field_filters,
                                    'delimiter': delimiter,
                                    'max_rows': max_rows},
                              timeout=CSV_TIMEOUT
                              )
        content = result.content
        logger.info('got content for csv')
        session.close()
        return content

    def generate_csv_field(self, entity_type: str, entity_id: str, field_name: str, sort: str = None,
                           desc: bool = False, search_text: str = ''):
        session = requests.Session()
        cookies = self.driver.get_cookies()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])
        session.headers['X-CSRF-Token'] = self.get_csrf_token()
        logger.info('posting for csv')
        result = session.post(f'https://127.0.0.1/api/{entity_type}/{entity_id}/{field_name}/csv',
                              json={'sort': sort, 'desc': ('1' if desc else '0'), 'search': search_text},
                              timeout=CSV_TIMEOUT
                              )
        content = result.content
        logger.info('got content for csv')
        session.close()
        return content

    def assert_csv_match_ui_data(self, result, ui_data=None, ui_headers=None, sort_columns=True, max_rows=MAX_ROWS_LEN):
        self.assert_csv_match_ui_data_with_content(result, max_rows, ui_data, ui_headers, sort_columns)

    @staticmethod
    def handle_bom(content):
        had_bom = 0
        while isinstance(content, bytes) and content.startswith(codecs.BOM_UTF8):
            had_bom += 1
            content = content[len(codecs.BOM_UTF8):]
        while isinstance(content, str) and content.startswith(codecs.BOM_UTF8.decode('utf-8')):
            had_bom += 1
            content = content[len(codecs.BOM_UTF8.decode('utf-8')):]
            assert had_bom == 2
        return content

    # pylint: disable=too-many-locals, too-many-branches
    def assert_csv_match_ui_data_with_content(self, content, max_rows=MAX_ROWS_LEN, ui_data=None, ui_headers=None,
                                              sort_columns=True, exclude_column_indexes=None):
        content = self.handle_bom(content)
        all_csv_rows = content.decode('utf-8').split('\r\n')
        csv_headers = all_csv_rows[0].split(',')
        csv_data_rows = all_csv_rows[1:-1]
        if not ui_headers:
            ui_headers = self.get_columns_header_text()
        if not ui_data:
            ui_data = self.get_all_data()
        ui_data_rows = [row.split('\n')[1:] for row in ui_data]
        # we don't writ image to csv
        if 'Image' in ui_headers:
            ui_headers.remove('Image')

        ui_headers_cmp = ui_headers
        csv_headers_cmp = [x.strip('"') for x in csv_headers]

        has_agg = any([x.startswith('Aggregated: ') for x in csv_headers_cmp])

        if has_agg:
            ui_headers_cmp = ['Aggregated: {head}'.format(head=head) for head in ui_headers]
        if sort_columns:
            ui_headers_cmp = sorted(ui_headers_cmp)
            csv_headers_cmp = sorted(csv_headers_cmp)

        if any(csv_data_rows) or any(ui_data_rows):
            for idx, ui_header in enumerate(csv_headers_cmp):
                if exclude_column_indexes and idx in exclude_column_indexes:
                    continue
                csv_header = ui_headers_cmp[idx]
                assert ui_header == csv_header

        # for every cell in the ui_data_rows we check if its in the csv_data_row
        # the reason we check it is because the csv have more columns with data
        # than the columns that we getting from the ui (boolean in the ui are represented by the css)
        for index, data_row in enumerate(csv_data_rows[:max_rows]):
            for cell_index, ui_data_cell in enumerate(ui_data_rows[index]):
                if exclude_column_indexes and cell_index in exclude_column_indexes:
                    continue
                cell_value = ui_data_cell.strip().split(', ')[0]
                # the boolean field return 'Yes' or 'No' instead of the regular true/false boolean
                # so we do a little hack on the returned data from the UI
                # if the cell value is the words 'Yes' or 'No' only we will change the value to True or False
                fixed_for_boolean = cell_value
                if fixed_for_boolean == 'Yes':
                    fixed_for_boolean = 'True'
                elif fixed_for_boolean == 'No':
                    fixed_for_boolean = 'False'
                assert normalize_timezone_date(cell_value) in data_row or fixed_for_boolean in data_row

    def assert_csv_field_match_ui_data(self, result):
        self.assert_csv_match_ui_data(result, self.get_field_data(), self.get_field_columns_header_text())

    def query_json_adapter(self):
        self.run_filter_query(JSON_ADAPTER_FILTER)

    def query_printer_device(self):
        self.run_filter_query(self.PRINTER_DEVICE_FILTER)

    def run_filter_query(self, filter_value: str):
        """
        Performs a filter on the entities table and waits for results
        :param filter_value: the filter to run
        :return:
        """
        self.fill_filter(filter_value)
        self.enter_search()
        self.wait_for_table_to_load()
        self.wait_for_spinner_to_end()

    def is_actions_button_disable(self):
        return self.has_class(self.get_button(self.ACTIONS_BUTTON), self.ACTIONS_BUTTON_DISABLED_CLASS)

    def open_actions_menu(self):
        self.click_button(self.ACTIONS_BUTTON)
        time.sleep(0.1)  # wait for menu to open

    def open_columns_menu(self):
        self.click_button(self.EDIT_COLUMNS_BUTTON)
        time.sleep(0.1)  # wait for menu to open

    def open_delete_dialog(self):
        self.open_actions_menu()
        self.driver.find_element_by_id(self.TABLE_ACTIONS_DELETE).click()

    def open_link_dialog(self):
        self.open_actions_menu()
        self.driver.find_element_by_id(self.TABLE_ACTIONS_LINK_DEVICES).click()

    def confirm_link(self):
        self.click_button('Save')

    def open_unlink_dialog(self):
        self.open_actions_menu()
        self.driver.find_element_by_id(self.TABLE_ACTIONS_UNLINK_DEVICES).click()

    def read_delete_dialog(self):
        return self.wait_for_element_present_by_css('.actions .modal-body .warn-delete').text

    def confirm_delete(self):
        self.click_button(self.DELETE_BUTTON)
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS)

    def refresh_table(self):
        self.enter_search()
        self.wait_for_table_to_load()

    def find_advanced_view(self):
        return self.driver.find_element_by_css_selector(self.CONFIG_ADVANCED_TEXT_CSS)

    def click_advanced_view(self):
        self.find_advanced_view().click()

    def find_basic_view(self):
        return self.get_button(self.CONFIG_BASIC_TEXT)

    def click_basic_view(self):
        self.find_basic_view().click()

    def load_notes(self, entities_filter=None):
        self.switch_to_page()
        if entities_filter:
            self.fill_filter(entities_filter)
            self.enter_search()
        self.wait_for_table_to_load()
        self.click_row()
        self.click_notes_tab()

    def load_custom_data(self, entities_filter=None):
        self.switch_to_page()
        if entities_filter:
            self.fill_filter(entities_filter)
            self.enter_search()
        self.wait_for_table_to_load()
        self.click_row()
        self.click_custom_data_tab()

    def get_entity_id(self):
        if len(self.find_elements_by_text(self.ID_FIELD)) == 0:
            return None
        return self.find_element_by_text(self.ID_FIELD).text

    def find_custom_data_edit(self):
        return self.get_enabled_button(self.CUSTOM_DATA_EDIT_BTN)

    def click_custom_data_edit(self):
        return self.find_custom_data_edit().click()

    def is_custom_data_edit_disabled(self):
        self.wait_for_element_present_by_xpath(
            self.DISABLED_BUTTON_XPATH.format(button_text=self.CUSTOM_DATA_EDIT_BTN))
        return True

    def click_custom_data_add_predefined(self):
        return self.click_button('Add Predefined field')

    def click_custom_data_add_new(self):
        return self.click_button('Add New field')

    def find_custom_data_save(self, context=None):
        if not context:
            context = self.driver.find_element_by_css_selector(self.ADAPTERS_DATA_TAB_CSS)
        return self.get_button(self.SAVE_BUTTON, context=context)

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

    def find_custom_data_value(self, parent=None, input_type_string=False):
        css_to_use = self.CUSTOM_DATA_FIELD_STRING_VALUE_CSS if input_type_string else self.CUSTOM_DATA_FIELD_VALUE_CSS
        if not parent:
            parent = self.driver
        return parent.find_element_by_css_selector(css_to_use)

    def select_custom_data_field(self, field_name, parent=None):
        self.select_option(self.CUSTOM_DATA_PREDEFINED_FIELD_CSS, self.DROPDOWN_TEXT_BOX_CSS,
                           self.DROPDOWN_SELECTED_OPTION_CSS, field_name, parent)

    def select_custom_data_field_type(self, field_type, parent=None):
        self.select_option(self.CUSTOM_DATA_NEW_FIELD_TYPE_CSS, self.DROPDOWN_TEXT_BOX_CSS,
                           self.DROPDOWN_SELECTED_OPTION_CSS, field_type, parent)

    def fill_custom_data_field_name(self, field_name, parent=None):
        self.fill_text_field_by_css_selector(self.CUSTOM_DATA_NEW_FIELD_NAME_CSS, field_name, parent)

    def fill_custom_data_value(self, field_value, parent=None, input_type_string=False):
        css_to_use = self.CUSTOM_DATA_FIELD_STRING_VALUE_CSS if input_type_string else self.CUSTOM_DATA_FIELD_VALUE_CSS
        self.fill_text_field_by_css_selector(css_to_use, field_value, parent)

    def save_custom_data(self):
        self.find_custom_data_save().click()
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS)

    def save_custom_data_feedback(self, context=None):
        self.find_custom_data_save(context).click()
        self.wait_for_element_present_by_xpath(self.FEEDBACK_MODAL_MESSAGE_XPATH.format(message='Custom data saved'))
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS)

    def clear_custom_data_field(self):
        self.click_remove_sign()

    def is_custom_error(self, error_text=None):
        if not error_text:
            self.wait_for_element_absent_by_css(self.CUSTOM_DATA_ERROR_CSS)
            return True
        return error_text == self.driver.find_element_by_css_selector(self.CUSTOM_DATA_ERROR_CSS).text

    def open_custom_data_bulk(self):
        self.open_actions_menu()
        self.driver.find_element_by_id(self.TABLE_ACTIONS_CUSTOM_DATA).click()

    def is_enforcement_results_header(self, enforcement_name, action_name):
        header_text = self.driver.find_element_by_css_selector('.x-query-state .header').text
        return (self.ENFORCEMENT_RESULTS_TITLE_END in header_text
                and enforcement_name in header_text
                and self.ENFORCEMENT_RESULTS_SUBTITLE.format(action_name=action_name) in header_text)

    def find_missing_email_server_notification(self):
        return self.find_element_by_text(self.MISSING_EMAIL_SETTINGS_TEXT)

    def click_expand_row(self, index=1):
        self.driver.find_element_by_css_selector(self.TABLE_ROW_EXPAND_CSS.format(child_index=index)).click()

    def click_expand_cell(self, row_index=1, cell_index=1):
        ActionChains(self.driver).move_to_element(self.driver.find_element_by_css_selector(
            self.TABLE_CELL_CSS.format(cell_index=cell_index))).perform()
        self.driver.find_element_by_css_selector(self.TABLE_CELL_EXPAND_CSS.format(
            row_index=row_index, cell_index=cell_index)).click()

    def hover_remainder(self, row_index=1, cell_index=1):
        remainder = self.driver.find_element_by_css_selector(
            self.TABLE_CELL_HOVER_REMAINDER_CSS.format(row_index=row_index, cell_index=cell_index))
        if remainder:
            ActionChains(self.driver).move_to_element(remainder).perform()
            return int(remainder.find_element_by_tag_name('span').text)
        return 0

    def get_hover_images_texts(self, cell):
        images = cell.find_elements_by_css_selector('img')
        values = []
        if images:
            for index, image in enumerate(images):
                ActionChains(self.driver).move_to_element(image).perform()
                tooltip_data = self.get_old_tooltip_table_data()
                if tooltip_data and len(tooltip_data) == 2:
                    values.append(tooltip_data[1].text)
        return values

    def get_tooltip_table_head(self):
        return self.driver.find_element_by_css_selector(self.TOOLTIP_TABLE_HEAD_CSS).text

    def get_old_tooltip_table_data(self):
        return self.driver.find_elements_by_css_selector(self.OLD_TOOLTIP_TABLE_DATA_CSS)

    def get_tooltip_table_data(self):
        return self.driver.find_elements_by_css_selector(self.TOOLTIP_TABLE_DATA_CSS)

    def get_coloumn_data_count_bool(self, col_name, count_true=False, generic_col=True):
        count_class = 'data-true' if count_true else 'data-false'
        col_position = self.count_sort_column(col_name) if generic_col else self.count_specific_column(col_name)
        return [len(el.find_elements_by_css_selector(f'.x-boolean-view .{count_class}')) for el in
                self.driver.find_elements_by_xpath(self.TABLE_DATA_XPATH.format(data_position=col_position))]

    def get_column_data_count_false(self, col_name, generic_col=True):
        return self.get_coloumn_data_count_bool(col_name, generic_col=generic_col)

    def wait_close_column_details_popup(self):
        self.wait_for_element_absent_by_css('.ant-popover .content .table')

    def find_query_header(self):
        return self.driver.find_element_by_css_selector('.x-query .x-query-state .header')

    def find_query_title_text(self):
        return self.find_query_header().find_element_by_css_selector('.query-title').text

    def find_query_status_text(self):
        return self.find_query_header().find_element_by_css_selector('.status').text

    def clear_custom_search_input(self):
        element = self.driver.find_element_by_css_selector(self.CUSTOM_DATA_SEARCH_INPUT)
        element.clear()

    def fill_custom_data_search_input(self, text):
        self.fill_text_field_by_css_selector(self.CUSTOM_DATA_SEARCH_INPUT, text)
        self.key_down_enter(self.driver.find_element_by_css_selector(self.CUSTOM_DATA_SEARCH_INPUT))

    def get_all_entity_active_custom_data_tab_table_rows(self) -> typing.List[TableRow]:
        """
        Note: this only returns the first page only
        """
        headers = [header.text for header in self.driver.find_elements_by_css_selector(
            self.ACTIVE_TAB_TABLE_ROWS_HEADERS) if header.text]
        return [TableRow(elem, headers=headers) for elem in
                self.driver.find_elements_by_css_selector(self.ACTIVE_TAB_TABLE_ROWS) if elem.text]

    def search_enforcement_tasks_search_input(self, text):
        self.fill_text_field_by_css_selector(self.ENFORCEMENT_SEARCH_INPUT, text)
        self.key_down_enter(self.driver.find_element_by_css_selector(self.ENFORCEMENT_SEARCH_INPUT))

    def get_enforcement_tasks_count(self):
        return len([row for row in self.get_all_table_rows(False) if len(row) > 1])

    def click_task_name(self, task_name):
        self.find_element_by_xpath(self.TASKS_TAB_TASK_NAME_XPATH.format(task_name=task_name)).click()

    def create_saved_query(self, data_query, query_name, query_description=None,
                           add_col_names=None, remove_col_names=None):
        self.switch_to_page()
        self.reset_query()
        self.fill_filter(data_query)
        self.enter_search()
        if add_col_names or remove_col_names:
            self.edit_columns(add_col_names, remove_col_names)
        self.click_save_query()
        self.fill_query_name(query_name)
        if query_description:
            self.fill_query_description(query_description)
        self.click_save_query_save_button(query_name=query_name)

    def open_filter_out_dialog(self):
        self.open_actions_menu()
        self.driver.find_element_by_id(self.TABLE_ACTIONS_FILTER_OUT).click()

    def confirm_filter_out(self):
        self.click_button('Yes')

    def click_filter_out_clear(self):
        self.driver.find_element_by_css_selector('.remove-filter-out').click()

    def get_adapters_popup_table_data(self):
        return self.get_table_data(self.ADAPTERS_TOOLTIP_TABLE_CSS, ['Adapters', 'Name'])

    def hover_entity_adapter_icon(self, index=0, clickable_rows=True):
        table_rows = self.get_all_table_rows_elements(clickable_rows=clickable_rows)
        table_row = table_rows[index]
        adapter_column = table_row.find_element_by_css_selector(self.ADAPTERS_COLUMN)
        ActionChains(self.driver).move_to_element(adapter_column).perform()

    def unhover_entity_adapter_icon(self):
        tooltip = self.get_entity_adapter_tooltip_table()
        ActionChains(self.driver).move_to_element_with_offset(tooltip, -200, -200).perform()

    def get_entity_adapter_tooltip_table(self):
        return self.driver.find_element_by_css_selector(self.ADAPTERS_TOOLTIP_TABLE_CSS)

    @retry(stop_max_delay=10000, wait_fixed=500)
    def assert_entity_adapter_tooltip_table(self, index=0, clickable_rows=True):
        self.hover_entity_adapter_icon(index, clickable_rows)
        assert self.get_entity_adapter_tooltip_table()

    def get_table_scroll_position(self):
        return self.get_scroll_position(self.TABLE_CONTAINER_CSS)

    def set_table_scroll_position(self, scroll_top: int, scroll_left: int):
        self.set_scroll_position(self.TABLE_CONTAINER_CSS, scroll_top, scroll_left)

    def select_query_filter(self, attribute='',  operator='', value='', clear_filter=False):

        if clear_filter:
            self.clear_query_wizard()

        expressions = self.find_expressions()
        self.select_query_field(attribute, parent=expressions[0])
        self.select_query_comp_op(operator, parent=expressions[0])
        if operator == COMP_EQUALS:
            self.select_query_value_without_search(value, parent=expressions[0])
        elif operator == COMP_IN:
            self.fill_query_string_value(value, parent=expressions[0])

    def select_query_with_adapter(self, adapter_name='JSON', attribute='',  operator='', value=''):
        expressions = self.find_expressions()
        self.select_query_adapter(adapter_name, parent=expressions[0])
        self.select_query_field(attribute, parent=expressions[0])
        self.select_query_comp_op(operator, parent=expressions[0])
        self.fill_query_value(value, parent=expressions[0])

    def click_tag_save_button(self):
        self.click_button(self.SAVE_BUTTON, context=self.driver.find_element_by_css_selector(self.TAG_MODAL_CSS))

    def open_tag_dialog(self):
        self.open_actions_menu()
        self.click_actions_tag_button()

    def add_new_tags(self, tags, number=1):
        self.open_tag_dialog()
        self.create_save_tags(tags, number)
        self.wait_for_table_to_load()

    def toggle_partial_tag(self, tag_text):
        partial_tag_elem = self.driver.find_element_by_xpath(self.TAG_CHECKBOX_XPATH.format(tag_text=tag_text))
        partial_tag_icon_ele = self.driver.find_element_by_xpath(self.TAG_PARTIAL_INPUT_ICON.format(tag_text=tag_text))
        partial_tag_input_elem = self.driver.find_element_by_xpath(self.TAG_PARTIAL_INPUT_CSS.format(tag_text=tag_text))
        partial_tag_elem.click()
        return {
            'tag_icon_ele': partial_tag_icon_ele,
            'tag_input_ele': partial_tag_input_elem
        }

    def set_partial_tag_to_state(self, tag):
        partial_tag_elem = self.driver.find_element_by_xpath(self.TAG_CHECKBOX_XPATH.format(tag_text=tag['name']))
        partial_tag_icon_ele = self.driver.find_element_by_xpath(self.TAG_PARTIAL_INPUT_ICON.
                                                                 format(tag_text=tag['name']))
        if tag['state'] == self.PartialState['CHECKED']:
            # set the partial tag to be checked
            partial_tag_elem.click()
        elif tag['state'] == self.PartialState['UNCHECKED']:
            # set the partial tag to be checked
            partial_tag_elem.click()
            # set the partial tag to be unchecked
            partial_tag_elem.click()
        return partial_tag_icon_ele

    def remove_all_tags(self, tags):
        self.toggle_select_all_rows_checkbox()
        self.click_select_all_entities()
        self.open_tag_dialog()
        for tag in tags:
            partial_tag_elem = self.driver.find_element_by_xpath(self.TAG_CHECKBOX_XPATH.format(tag_text=tag))
            partial_tag_icon_ele = self.driver.find_element_by_xpath(self.TAG_PARTIAL_INPUT_ICON.
                                                                     format(tag_text=tag))
            if self.has_class(partial_tag_icon_ele, self.PartialIcon['CHECKED']):
                partial_tag_elem.click()
            elif self.has_class(partial_tag_icon_ele, self.PartialIcon['PARTIAL']):
                # set to chekced
                partial_tag_elem.click()
                # set to unchecked
                partial_tag_elem.click()
        self.click_tag_save_button()

    def create_save_tags(self, tags, number=1):
        for tag_text in tags:
            self.fill_text_field_by_css_selector(self.TAGS_TEXTBOX_CSS, tag_text)
            time.sleep(0.1)
            self.click_create_new_tag_link_button()
            self.wait_for_element_present_by_xpath(self.TAG_NEW_ITEM_XPATH.format(tag_text=tag_text))
        self.click_tag_save_button()
        self.wait_for_success_tagging_message(number)
        self.wait_for_spinner_to_end()

    def remove_first_tag(self):
        self.open_tag_dialog()
        self.wait_for_element_present_by_css(self.TAG_CHECKBOX_CSS).click()
        self.click_tag_save_button()
        self.wait_for_success_tagging_message()
        self.wait_for_table_to_load()

    def remove_tag(self, text):
        self.open_tag_dialog()
        self.find_element_by_text(text).click()
        self.click_tag_save_button()
        self.wait_for_success_tagging_message()

    def get_first_tag_text(self):
        return self.get_first_row_tags().splitlines()[0]

    def get_first_row_tags(self):
        return self.driver.find_elements_by_css_selector(self.TABLE_FIRST_ROW_TAG_CSS)[0].text

    def wait_for_success_tagging_message(self, number=1):
        return NotImplementedError()

    def wait_for_success_tagging_message_for_entities(self, number=1, success_message='{}'):
        message = self.FEEDBACK_MODAL_MESSAGE_XPATH.format(message=success_message.format(number=number))
        self.wait_for_element_present_by_xpath(message)
        self.wait_for_element_absent_by_xpath(message)

    def get_tag_combobox_exist(self):
        return self.wait_for_element_present_by_css(self.TAG_COMBOBOX_CSS)

    def get_tag_modal_info(self):
        return self.driver.find_element_by_css_selector('.tag-modal-info')

    def get_checkbox_list(self):
        return self.driver.find_elements_by_css_selector('.v-list-item')

    def get_tags_input(self):
        return self.driver.find_element_by_css_selector(self.TAGS_TEXTBOX_CSS)

    def click_create_new_tag_link_button(self):
        return self.driver.find_element_by_css_selector(self.TAG_CREATE_NEW_CSS).click()

    def is_tags_input_text_selectable(self):
        return self.is_input_text_selectable(self.TAGS_TEXTBOX_CSS)

    def fill_tags_input_text(self, text):
        self.fill_text_by_element(self.get_tags_input(), text)

    def close_actions_dropdown(self):
        el = self.driver.find_element_by_css_selector(self.ENTITIES_ACTIONS_DROPDOWN_CSS)
        ActionChains(self.driver).move_to_element_with_offset(el, 250, 100).click().perform()

    @staticmethod
    def wait_for_csv_to_update_cache():
        # wait for heavy lifting to clear its 60 seconds cache
        time.sleep(61)

    def get_saved_query_value(self, parent):
        if parent:
            el = parent.find_element_by_css_selector(self.QUERY_VALUE_COMPONENT_CSS)
        else:
            el = self.wait_for_element_present_by_css(self.QUERY_VALUE_COMPONENT_CSS)
        return el.get_attribute('innerText')

    def create_saved_query_with_reference(self, origin_name, targets):
        for index, target_name in enumerate(targets):
            self.click_query_wizard()
            if index > 0:
                self.add_query_expression()
            expressions = self.find_expressions()
            assert len(expressions) == index + 1
            self.select_query_field(self.FIELD_SAVED_QUERY, parent=expressions[index])
            self.select_saved_query_reference(target_name, parent=expressions[index])
        self.save_query_as(origin_name)
        self.reset_query()

    def select_saved_query_reference(self, target_name, parent):
        self.select_query_value(target_name, parent=parent)
        self.wait_for_table_to_be_responsive()
        self.close_dropdown()

    def create_base_query_for_reference(self, query_name):
        self.click_query_wizard()
        expressions = self.find_expressions()
        assert len(expressions) == 1
        self.select_query_field(self.FIELD_ASSET_NAME, parent=expressions[0])
        self.select_query_comp_op(COMP_CONTAINS, parent=expressions[0])
        self.fill_query_string_value('CB 1', parent=expressions[0])
        self.wait_for_table_to_be_responsive()
        self.close_dropdown()
        self.save_query_as(query_name)
        self.reset_query()

    def execute_and_assert_query_reference(self, origin_name, targets):
        self.execute_saved_query(origin_name)
        self.wait_for_table_to_be_responsive()
        assert self.get_table_count() == 1
        self.click_query_wizard()
        expressions = self.find_expressions()
        assert len(expressions) == len(targets)
        for index, target_name in enumerate(targets):
            assert self.get_saved_query_value(parent=expressions[index]) == target_name
        self.close_dropdown()

    def get_saved_queries_options(self, parent):
        parent.find_element_by_css_selector(self.QUERY_VALUE_COMPONENT_CSS).click()
        time.sleep(0.5)
        options = parent.find_elements_by_css_selector(self.SAVED_QUERY_OPTIONS_CSS)
        return [option.text for option in options]
