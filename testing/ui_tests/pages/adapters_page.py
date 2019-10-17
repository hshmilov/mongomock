import time
from collections import namedtuple
from copy import copy
import re

from selenium.common.exceptions import NoSuchElementException

from test_helpers.file_mock_credentials import FileForCredentialsMock
from ui_tests.pages.entities_page import EntitiesPage
from ui_tests.pages.page import PAGE_BODY, SLEEP_INTERVAL, RETRY_WAIT_FOR_ELEMENT
from ui_tests.tests.ui_consts import AD_ADAPTER_NAME

# NamedTuple doesn't need to be uppercase
# pylint: disable=C0103
Adapter = namedtuple('Adapter', 'name description')


class AdaptersPage(EntitiesPage):
    ROOT_PAGE_CSS = 'li#adapters.x-nav-item'
    SEARCH_TEXTBOX_CSS = 'div.x-search-input > input.input-value'
    TABLE_ROW_CLASS = 'table-row'
    TABLE_CLASS = '.table'
    TEST_CONNECTIVITY = 'Test Reachability'
    RT_CHECKBOX_CSS = '[for=realtime_adapter]+div'
    ADVANCED_SETTINGS_SAVE_BUTTON_CSS = '.x-tab.active .configuration>.x-button'

    TEST_CONNECTIVITY_CONNECTION_IS_VALID = 'Connection is valid.'
    TEST_CONNECTIVITY_NOT_SUPPORTED = 'Test reachability is not supported for this adapter.'
    TEST_CONNECTIVITY_PROBLEM = 'Problem connecting'

    SERVER_ORANGE_COLOR_ID = 'svgicon_symbol_warning_a'
    SERVER_RED_COLOR_ID = 'svgicon_symbol_error_a'
    SERVER_GREEN_COLOR_ID = 'svgicon_symbol_success_a'
    ERROR_SYMBOL_ID = 'svgicon_symbol_error_b'
    WARNING_MARKER_CSS = '.marker.indicator-bg-warning'
    RED_COLOR_ID = 'svgicon_symbol_error_b'
    GREEN_COLOR_ID = 'svgicon_symbol_success_b'
    NEW_CONNECTION_BUTTON_ID = 'new_connection'
    DATA_COLLECTION_TOASTER = 'Connection established. Data collection initiated...'
    TEXT_PROBLEM_CONNECTING_TRY_AGAIN = 'Problem connecting. Review error and try again.'

    DELETE_ASSOCIATED_ENTITIES_CHECKBOX_ID = 'deleteEntitiesCheckbox'
    AD_SERVER_SEARCH_FIELD = ('dc_name', 'DC Address')
    ADAPTER_INSTANCE_CONFIG_CSS_SELECTOR = '.config-server'
    EDIT_INSTANCE_XPATH = '//div[@title=\'{instance_name}\']/parent::td/parent::tr'

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
        self.click_button(self.SAVE_AND_CONNECT_BUTTON)

    def click_cancel(self):
        self.click_button(self.CANCEL_BUTTON, button_class='x-button link')

    def click_test_connectivity(self):
        self.click_button(self.TEST_CONNECTIVITY)

    def assert_new_server_button_is_disabled(self):
        assert self.is_element_disabled_by_id(self.NEW_CONNECTION_BUTTON_ID)

    def click_new_server(self):
        self.click_button_by_id(self.NEW_CONNECTION_BUTTON_ID,
                                call_space=False,
                                should_scroll_into_view=False,
                                scroll_into_view_container=PAGE_BODY)

    def click_advanced_settings(self):
        self.find_element_by_text('Advanced Settings').click()
        time.sleep(1.5)

    def click_advanced_configuration(self):
        self.find_element_by_text('Adapter Configuration').click()
        time.sleep(1.5)

    def save_advanced_settings(self):
        self.driver.find_element_by_css_selector(self.ADVANCED_SETTINGS_SAVE_BUTTON_CSS).click()

    def check_rt_adapter(self):
        self.driver.find_element_by_css_selector(self.RT_CHECKBOX_CSS).click()

    def assert_screen_is_restricted(self):
        self.switch_to_page_allowing_failure()
        self.find_element_by_text('You do not have permission to access the Adapters screen')
        self.click_ok_button()

    def select_all_servers(self):
        self.driver.find_element_by_css_selector(self.CHECKBOX_CSS).click()

    def wait_for_server_green(self):
        self.wait_for_element_present_by_id(self.SERVER_GREEN_COLOR_ID)

    def wait_for_server_red(self):
        self.wait_for_element_present_by_id(self.SERVER_RED_COLOR_ID)

    def wait_for_adapter_green(self):
        self.wait_for_element_present_by_id(self.GREEN_COLOR_ID)

    def wait_for_adapter_red(self):
        self.wait_for_element_present_by_id(self.RED_COLOR_ID)

    def wait_for_adapter_warning(self):
        self.wait_for_element_present_by_id(self.ERROR_SYMBOL_ID)
        self.wait_for_element_present_by_css(self.WARNING_MARKER_CSS)

    def wait_for_connect_valid(self):
        self.wait_for_element_present_by_text(self.TEST_CONNECTIVITY_CONNECTION_IS_VALID)

    def wait_for_test_connectivity_not_supported(self):
        self.wait_for_element_present_by_text(self.TEST_CONNECTIVITY_NOT_SUPPORTED)

    def wait_for_problem_connecting_to_server(self):
        self.wait_for_element_present_by_text(self.TEST_CONNECTIVITY_PROBLEM)

    def wait_for_problem_connecting_try_again(self, retries=RETRY_WAIT_FOR_ELEMENT, interval=SLEEP_INTERVAL):
        self.wait_for_element_present_by_text(
            self.TEXT_PROBLEM_CONNECTING_TRY_AGAIN,
            retries=retries,
            interval=interval)

    def clean_adapter_servers(self, name, delete_associated_entities=False):
        self.remove_server(None, name, delete_associated_entities=delete_associated_entities)

    def remove_server(self, ad_client=None, adapter_name=AD_ADAPTER_NAME, adapter_search_field=AD_SERVER_SEARCH_FIELD,
                      delete_associated_entities=False):
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
            return self.find_element_by_text('Help')
        except NoSuchElementException:
            return None

    def click_help_link(self):
        self.find_help_link().click()

    def find_status_symbol(self, status_type):
        return self.wait_for_element_present_by_css(f'#svgicon_symbol_{status_type}_b')

    def find_status_count(self, status_type):
        element = self.wait_for_element_present_by_css(f'.status_{status_type} .status_clients-count')
        return element.text

    def get_adapters_table_length(self):
        adapters = self.get_adapter_list()
        return len(adapters)

    def click_connected_adapters_filter_switch(self):
        element = self.wait_for_element_present_by_css('.adapters-search .md-switch-thumb')
        element.click()

    def get_connected_adapters_number_form_switch_label(self):
        pattern = r'configured only \((\d)\)'

        element = self.wait_for_element_present_by_css('.adapters-search .md-switch-label')
        element_text = element.text

        match_object = re.match(pattern, element_text, re.I | re.M)
        return match_object.group(1)
