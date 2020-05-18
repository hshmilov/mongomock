import re
import time
from collections import namedtuple
from copy import copy

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement

from axonius.utils.wait import wait_until
from test_credentials.json_file_credentials import (CLIENT_DETAILS_EXTRA,
                                                    FILE_NAME)
from test_helpers.file_mock_credentials import FileForCredentialsMock
from ui_tests.pages.entities_page import EntitiesPage
from ui_tests.pages.page import (PAGE_BODY, RETRY_WAIT_FOR_ELEMENT,
                                 SLEEP_INTERVAL)
from ui_tests.tests.ui_consts import (AD_ADAPTER_NAME, CSV_NAME,
                                      JSON_ADAPTER_NAME)

# NamedTuple doesn't need to be uppercase
# pylint: disable=C0103
Adapter = namedtuple('Adapter', 'name description')
CONNECTION_LABEL = 'AXON'
CONNECTION_LABEL_UPDATED = 'AXON2'
TANIUM_ADAPTERS_CONNECTION_LABEL_UPDATED = '4250'
ADAPTER_THYCOTIC_VAULT_BUTTON = 'cyberark-button'
ADAPTER_THYCOTIC_VAULT_QUERY_ID = 'cyberark-query'
ADAPTER_THYCOTIC_VAULT_ICON = '.cyberark-icon .md-icon'


class AdaptersPage(EntitiesPage):
    ROOT_PAGE_CSS = 'li#adapters.x-nav-item'
    SEARCH_TEXTBOX_CSS = 'div.x-search-input > input.input-value'
    TABLE_ROW_CLASS = 'table-row'
    TABLE_CLASS = '.table'
    TEST_CONNECTIVITY = 'Test Reachability'
    RT_CHECKBOX_CSS = '[for=realtime_adapter]+div'
    CHECKBOX_CLASS = 'x-checkbox'
    CHECKED_CHECKBOX_CLASS = 'x-checkbox checked'
    ADVANCED_SETTINGS_SAVE_BUTTON_CSS = '.x-tab.active .configuration>.x-button'
    ADVANCED_SETTINGS_BUTTON_TEXT = 'Advanced Settings'

    TEST_CONNECTIVITY_CONNECTION_IS_VALID = 'Connection is valid.'
    TEST_CONNECTIVITY_NOT_SUPPORTED = 'Test reachability is not supported for this adapter.'
    TEST_CONNECTIVITY_PROBLEM = 'Problem connecting'
    TEST_CREDENTIALS_PROBLEM = 'Failed to save connection details. ' \
                               'Changing connection details requires re-entering credentials'

    ERROR_ICON_CLASS = '.md-icon.icon-error'
    SUCCESS_ICON_CLASS = '.x-table-row:nth-child({position}) .md-icon.icon-success'
    ADAPTERS_SUCCESS_ICON_CLASS = '.adapters-table .table-row:nth-child({position}) .md-icon.icon-success'
    TYPE_ICON_CSS = '.md-icon.icon-{status_type}'
    WARNING_MARKER_CSS = '.marker.indicator-bg-warning'
    NEW_CONNECTION_BUTTON_ID = 'new_connection'
    DATA_COLLECTION_TOASTER = 'Connection established. Data collection initiated...'
    TEXT_PROBLEM_CONNECTING_TRY_AGAIN = 'Problem connecting. Review error and try again.'
    SERVER_ERROR_TEXT_CLASS = '.server-error .error-text'

    DELETE_ASSOCIATED_ENTITIES_CHECKBOX_ID = 'deleteEntitiesCheckbox'
    AD_SERVER_SEARCH_FIELD = ('dc_name', 'DC Address')
    JSON_FILE_SERVER_SEARCH_FIELD = ('file_name', 'Name')
    ADAPTER_INSTANCE_CONFIG_CSS_SELECTOR = '.config-server'
    EDIT_INSTANCE_XPATH = '//div[@title=\'{instance_name}\']/parent::td/parent::tr'
    INSTANCE_DROPDOWN_CSS = '#serverInstance div.trigger-text'

    INPUT_TYPE_PWD_VALUE = '********'

    CSV_ADAPTER_QUERY = 'adapters_data.csv_adapter.id == exists(true)'
    CSV_FILE_NAME = 'file_path'  # Changed by Alex A on Jan 27 2020 - because schema changed
    CSV_INPUT_ID = 'file_path'  # Changed by Alex A on Jan 27 2020 - because schema changed

    @property
    def url(self):
        return f'{self.base_url}/adapters'

    @property
    def root_page_css(self):
        return self.ROOT_PAGE_CSS

    def search(self, text):
        text_box = self.driver.find_element_by_css_selector(self.SEARCH_TEXTBOX_CSS)
        self.fill_text_by_element(text_box, text)

    def get_adapter_list(self):
        result = []

        adapter_table = self.driver.find_element_by_css_selector(self.TABLE_CLASS)

        # Use from index 1 to avoid selecting the table head
        rows = adapter_table.find_elements_by_tag_name('tr')[1:]
        for row in rows:
            # Get the columns in order [status, name, description]
            # count = row.find_elements(By.TAG_NAME, 'td')[0]
            name = row.find_elements_by_tag_name('td')[1].text
            description = row.find_elements_by_tag_name('td')[2].text
            result.append(Adapter(name=name, description=description))

        return result

    def click_adapter(self, adapter_name):
        self.click_button(adapter_name,
                          button_class='x-title adapter-title',
                          button_type='div',
                          call_space=False,
                          scroll_into_view_container='.adapters-table')
        self.wait_for_table_to_load()

    def click_save(self):
        self.get_enabled_button(self.SAVE_AND_CONNECT_BUTTON).click()

    def is_save_button_disabled(self):
        return self.is_element_disabled(self.get_button(self.SAVE_AND_CONNECT_BUTTON))

    def click_cancel(self):
        context_element = self.wait_for_element_present_by_css('.x-modal.config-server')
        self.click_button(self.CANCEL_BUTTON, context=context_element)

    def click_test_connectivity(self):
        self.click_button(self.TEST_CONNECTIVITY)

    def assert_new_server_button_is_enabled(self):
        assert not self.is_element_disabled_by_id(self.NEW_CONNECTION_BUTTON_ID)

    def assert_new_server_button_is_disabled(self):
        assert self.is_element_disabled_by_id(self.NEW_CONNECTION_BUTTON_ID)

    def assert_servers_cant_be_opened(self):
        assert len(self.get_all_table_rows_elements()) == 0

    def assert_advanced_settings_is_enabled(self):
        assert self.get_enabled_button(self.ADVANCED_SETTINGS_BUTTON_TEXT)

    def assert_advanced_settings_is_disabled(self):
        assert self.is_element_disabled(self.get_button(self.ADVANCED_SETTINGS_BUTTON_TEXT))

    def click_new_server(self):
        self.click_button_by_id(self.NEW_CONNECTION_BUTTON_ID,
                                call_space=False,
                                should_scroll_into_view=False,
                                scroll_into_view_container=PAGE_BODY)

    def click_edit_server(self, index=0):
        self.get_all_table_rows_elements()[index].click()

    def click_edit_server_by_name(self, name):
        self.click_specific_row_by_field_value('Name', name)

    def click_advanced_settings(self):
        self.get_button(self.ADVANCED_SETTINGS_BUTTON_TEXT).click()
        time.sleep(1.5)

    def fill_last_seen_threshold_hours(self, value):
        self.fill_text_field_by_element_id('last_seen_threshold_hours', value)

    def click_advanced_configuration(self):
        self.find_element_by_text('Adapter Configuration').click()
        time.sleep(1.5)

    def save_advanced_settings(self):
        self.driver.find_element_by_css_selector(self.ADVANCED_SETTINGS_SAVE_BUTTON_CSS).click()

    def check_rt_adapter(self):
        self.driver.find_element_by_css_selector(self.RT_CHECKBOX_CSS).click()

    def select_all_servers(self):
        self.driver.find_element_by_css_selector(self.CHECKBOX_CSS).click()

    def wait_for_server_green(self, position=1, retries=300, interval=1):
        self.wait_for_element_present_by_css(self.SUCCESS_ICON_CLASS.format(position=position), retries=retries,
                                             interval=interval)

    def wait_for_adapter_green(self, position=1):
        self.wait_for_element_present_by_css(self.ADAPTERS_SUCCESS_ICON_CLASS.format(position=position),
                                             retries=300, interval=1)

    def wait_for_server_red(self):
        self.wait_for_element_present_by_css(self.ERROR_ICON_CLASS)

    def wait_for_adapter_warning(self):
        self.wait_for_element_present_by_css(self.ERROR_ICON_CLASS)
        self.wait_for_element_present_by_css(self.WARNING_MARKER_CSS)

    def wait_for_connect_valid(self):
        self.wait_for_element_present_by_text(self.TEST_CONNECTIVITY_CONNECTION_IS_VALID)

    def wait_for_test_connectivity_not_supported(self):
        self.wait_for_element_present_by_text(self.TEST_CONNECTIVITY_NOT_SUPPORTED)

    def wait_for_problem_connecting_to_server(self):
        self.wait_for_element_present_by_text(self.TEST_CONNECTIVITY_PROBLEM)

    def wait_for_credentials_problem_to_server(self):
        self.wait_for_element_present_by_text(self.TEST_CREDENTIALS_PROBLEM)

    def wait_for_problem_connecting_try_again(self, retries=RETRY_WAIT_FOR_ELEMENT, interval=SLEEP_INTERVAL):
        self.wait_for_element_present_by_text(
            self.TEXT_PROBLEM_CONNECTING_TRY_AGAIN,
            retries=retries,
            interval=interval)

    def clean_adapter_servers(self, name, delete_associated_entities=False):
        self.remove_server(None, name, delete_associated_entities=delete_associated_entities)

    def checkboxes_count(self):
        table_element = self.driver.find_element_by_css_selector(self.TABLE_CLASS)
        elements = table_element.find_elements_by_class_name(self.CHECKBOX_CLASS) + \
            table_element.find_elements_by_class_name(self.CHECKED_CHECKBOX_CLASS)
        return len(elements) - 1

    def _check_checkboxes_count(self):
        self.wait_for_table_to_load()
        count = self.checkboxes_count()
        return count

    def wait_for_elements_delete(self, expected_left):
        wait_until(lambda: self._check_checkboxes_count() == expected_left, total_timeout=60 * 5, interval=1)

    def remove_server(self, ad_client=None, adapter_name=AD_ADAPTER_NAME, adapter_search_field=AD_SERVER_SEARCH_FIELD,
                      delete_associated_entities=False, expected_left=0):
        self.switch_to_page()
        self.wait_for_spinner_to_end()
        self.click_adapter(adapter_name)
        self.wait_for_spinner_to_end()
        self.wait_for_table_to_load()
        if ad_client is None:
            self.select_all_servers()
        else:
            self.click_specific_row_checkbox(adapter_search_field[1], ad_client[adapter_search_field[0]])
        try:
            self.remove_selected()
        except NoSuchElementException:
            # we dont have element to remove, just return...
            return

        if delete_associated_entities:
            self.wait_for_element_present_by_id(self.DELETE_ASSOCIATED_ENTITIES_CHECKBOX_ID)
            self.click_toggle_button(self.driver.find_element_by_id(self.DELETE_ASSOCIATED_ENTITIES_CHECKBOX_ID),
                                     make_yes=True, scroll_to_toggle=False)

        self.approve_remove_selected()
        self.wait_for_elements_delete(expected_left=expected_left)

    def fill_creds(self, **kwargs):
        for key, value in kwargs.items():
            element = self.driver.find_element_by_id(key)
            if isinstance(value, FileForCredentialsMock):
                value: FileForCredentialsMock
                self.upload_file_on_element(element, value.file_contents)
            elif isinstance(value, bool):
                self.click_toggle_button(element, make_yes=value)
            else:
                self.fill_text_by_element(element, value)

    def verify_creds(self, **kwargs):
        for key, value in kwargs.items():
            element: WebElement = self.driver.find_element_by_id(key)
            if isinstance(value, bool):
                assert self.is_toggle_selected(element) == value
            elif isinstance(value, str):
                if element.get_attribute('type') == 'password':
                    if not value:
                        assert element.get_attribute('value') == ''
                    else:
                        assert element.get_attribute('value') == self.INPUT_TYPE_PWD_VALUE
                else:
                    assert element.get_attribute('value') == value
            else:
                assert False

    def wait_for_data_collection_toaster_absent(self):
        self.wait_for_toaster_to_end(self.DATA_COLLECTION_TOASTER, retries=1200)

    def wait_for_data_collection_toaster_start(self, retries=1200):
        self.wait_for_toaster(self.DATA_COLLECTION_TOASTER, retries)

    def wait_for_data_collection_failed_toaster_absent(self):
        self.wait_for_toaster_to_end(self.TEXT_PROBLEM_CONNECTING_TRY_AGAIN, retries=1200)

    def add_server(self, ad_client, adapter_name=AD_ADAPTER_NAME):
        self.switch_to_page()
        self.click_adapter(adapter_name)
        self.wait_for_table_to_load()
        self.wait_for_spinner_to_end()
        self.click_new_server()
        self.wait_for_element_present_by_css(self.MODAL_OVERLAY_CSS)
        dict_ = copy(ad_client)
        dict_.pop('use_ssl', None)
        dict_.pop('fetch_disabled_users', None)
        dict_.pop('verify_ssl', None)

        self.fill_creds(**dict_)
        self.click_save()

    def wait_for_adapter(self, adapter_name, retries=60 * 3, interval=2):
        for _ in range(retries):
            self.test_base.settings_page.switch_to_page()
            self.switch_to_page()
            try:
                element = self.find_element_by_text(adapter_name)
                if element:
                    return
            except NoSuchElementException:
                pass
            time.sleep(interval)

    def find_help_link(self):
        try:
            return self.get_button('Help')
        except NoSuchElementException:
            return None

    def click_help_link(self):
        self.find_help_link().click()

    def find_status_symbol(self, status_type):
        return self.wait_for_element_present_by_css(self.TYPE_ICON_CSS.format(status_type=status_type))

    def find_status_count(self, status_type):
        element = self.wait_for_element_present_by_css(
            f'{self.TYPE_ICON_CSS.format(status_type=status_type)} ~ .summary_count')
        return element.text

    def find_server_error(self):
        element = self.driver.find_element_by_css_selector(self.SERVER_ERROR_TEXT_CLASS)
        return element.text

    def get_adapters_table_length(self):
        adapters = self.get_adapter_list()
        return len(adapters)

    def click_connected_adapters_filter_switch(self):
        element = self.wait_for_element_present_by_css('.adapters-search .md-switch-thumb')
        element.click()

    def click_cyberark_button(self):
        element = self.driver.find_element_by_css_selector('.cyberark-icon .md-icon')
        element.click()

    def get_connected_adapters_number_form_switch_label(self):
        pattern = r'configured only \((\d)\)'

        element = self.wait_for_element_present_by_css('.adapters-search .md-switch-label')
        element_text = element.text

        match_object = re.match(pattern, element_text, re.I | re.M)
        return match_object.group(1)

    def create_new_adapter_connection(self, plugin_title: str, adapter_input: dict):
        self.wait_for_adapter(plugin_title)
        self.click_adapter(plugin_title)
        self.wait_for_table_to_load()
        self.click_new_server()
        self.fill_creds(**adapter_input)
        self.click_save()

    def get_instances_dropdown_selected_value(self):
        return self.driver.find_element_by_css_selector(self.INSTANCE_DROPDOWN_CSS).text

    def connect_adapter(self, adapter_name, server_details):
        self.wait_for_adapter(adapter_name)
        self.add_server(ad_client=server_details, adapter_name=adapter_name)
        self.wait_for_server_green()
        self.switch_to_page()

    def add_json_extra_client(self):
        self.add_server(CLIENT_DETAILS_EXTRA, adapter_name=JSON_ADAPTER_NAME)

    def remove_json_extra_client(self):
        self.remove_server(CLIENT_DETAILS_EXTRA, JSON_ADAPTER_NAME, adapter_search_field=(FILE_NAME, 'Name'),
                           expected_left=1)

    def edit_server_conn_label(self, adapter_name, connection_label):
        self.wait_for_adapter(adapter_name)
        self.click_adapter(adapter_name)
        self.wait_for_spinner_to_end()
        self.wait_for_table_to_load()
        self.click_edit_server()
        self.fill_creds(connectionLabel=connection_label)
        self.click_save()

    def upload_csv(self, csv_file_name, csv_data, is_user_file=False):
        self.open_add_edit_server(CSV_NAME)
        self.fill_upload_csv_form_with_csv(csv_file_name, csv_data, is_user_file)
        self.click_save()

    def fill_upload_csv_form_with_csv(self, csv_file_name, csv_data, is_user_file=False):
        self.upload_file_by_id(self.CSV_INPUT_ID, csv_data[csv_file_name].file_contents)
        self.fill_creds(user_id=csv_file_name, connectionLabel=csv_file_name)
        if is_user_file:
            self.find_checkbox_by_label('File contains users information').click()

    def open_add_edit_server(self, adapter_name, row_position=0):
        self.wait_for_adapter(adapter_name)
        self.click_adapter(adapter_name)
        self.wait_for_spinner_to_end()
        self.wait_for_table_to_load()
        if row_position == 0:
            self.click_new_server()
        else:
            self.click_edit_server(row_position - 1)

    def click_thycotic_button(self):
        element = self.driver.find_element_by_css_selector(ADAPTER_THYCOTIC_VAULT_ICON)
        element.click()

    def find_thycotic_vault_icon(self):
        return self.driver.find_element_by_id(ADAPTER_THYCOTIC_VAULT_BUTTON)

    def verify_thycotic_button_is_not_present(self):
        if len(self.driver.find_elements_by_id(ADAPTER_THYCOTIC_VAULT_BUTTON)):
            return False
        return True

    def assert_thycotic_vault_icon_appear(self):
        element = self.find_thycotic_vault_icon()
        assert element is not None

    def check_thycotic_fetch_status(self, should_succeed=True):
        thycotic_icon_element = self.driver.find_element_by_css_selector(ADAPTER_THYCOTIC_VAULT_ICON)
        class_attribute = 'success' if should_succeed else 'error'
        return class_attribute in thycotic_icon_element.get_attribute('class')

    def check_thycotic_success_status(self):
        assert self.check_thycotic_fetch_status(should_succeed=True)

    def check_thycotic_failure_status(self):
        assert self.check_thycotic_fetch_status(should_succeed=False)

    def fetch_password_from_thycotic_vault(self, screct_id: str, is_negative_test=False):
        # Waiting until cyberark icon is present
        wait_until(self.assert_thycotic_vault_icon_appear,
                   check_return_value=False,
                   tolerated_exceptions_list=[AssertionError, NoSuchElementException])
        self.click_thycotic_button()
        self.fill_text_field_by_element_id(ADAPTER_THYCOTIC_VAULT_QUERY_ID, screct_id)
        self.click_button('Fetch')

        if is_negative_test:
            wait_until(self.check_thycotic_failure_status,
                       check_return_value=False,
                       tolerated_exceptions_list=[AssertionError, NoSuchElementException])
        else:
            wait_until(self.check_thycotic_success_status,
                       check_return_value=False,
                       tolerated_exceptions_list=[AssertionError, NoSuchElementException])

    def find_server_connection_label_value(self):
        return self.driver.find_element_by_id('connectionLabel').get_attribute('value')
