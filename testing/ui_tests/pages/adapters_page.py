from collections import namedtuple
from copy import copy

from selenium.common.exceptions import NoSuchElementException

from ui_tests.pages.entities_page import EntitiesPage
from ui_tests.pages.page import X_BODY

# NamedTuple doesn't need to be uppercase
# pylint: disable=C0103
Adapter = namedtuple('Adapter', 'name description')
AD_NAME = 'Active Directory'


class AdaptersPage(EntitiesPage):
    ROOT_PAGE_CSS = 'li#adapters.x-nested-nav-item'
    SEARCH_TEXTBOX_CSS = 'div.search-input > input.input-value'
    TABLE_ROW_CLASS = 'table-row'
    TEST_CONNECTIVITY = 'Test Connectivity'
    DEVICE_CHECKBOX = 'div.x-checkbox-container'
    RT_CHECKBOX_CSS = '[for=realtime_adapter]+div'
    ADVANCED_SETTINGS_SAVE_BUTTON_CSS = '.configuration>a'

    TEST_CONNECTIVITY_CONNECTION_IS_VALID = 'Connection is valid.'
    TEST_CONNECTIVITY_NOT_SUPPORTED = 'Test connectivity is not supported for this adapter.'
    TEST_CONNECTIVITY_PROBLEM = 'Problem connecting to server.'

    SERVER_ORANGE_COLOR_ID = 'svgicon-symbol-warning-a'
    SERVER_RED_COLOR_ID = 'svgicon-symbol-error-a'
    SERVER_GREEN_COLOR_ID = 'svgicon-symbol-success-a'
    ORANGE_COLOR_ID = 'svgicon-symbol-warning-b'
    RED_COLOR_ID = 'svgicon-symbol-error-b'
    GREEN_COLOR_ID = 'svgicon-symbol-success-b'
    NEW_SERVER_BUTTON_ID = 'new_server'
    DATA_COLLECTION_TOASTER = 'Connection established. Data collection initiated...'

    DELETE_ASSOCIATED_ENTITIES_CHECKBOX_ID = 'deleteEntitiesCheckbox'
    AD_SERVER_SEARCH_FIELD = ('dc_name', 'DC Address')

    @property
    def url(self):
        return f'{self.base_url}/adapter'

    @property
    def root_page_css(self):
        return self.ROOT_PAGE_CSS

    def search(self, text):
        text_box = self.driver.find_element_by_css_selector(self.SEARCH_TEXTBOX_CSS)
        self.fill_text_by_element(text_box, text)

    def get_adapter_list(self):
        result = []

        adapter_table = self.driver.find_elements_by_class_name(self.TABLE_ROW_CLASS)

        # Skip the title row
        adapter_table = adapter_table[1:]

        for adapter_element in adapter_table:
            name, description = adapter_element.text.split('\n', 1)
            result.append(Adapter(name=name, description=description))

        return result

    def click_adapter(self, adapter_name):
        self.click_button(adapter_name, button_class='title', button_type='div', call_space=False)
        self.wait_for_table_to_load()

    def click_save(self):
        self.click_button(self.SAVE_BUTTON)

    def click_cancel(self):
        self.click_button(self.CANCEL_BUTTON, button_class='x-btn link')

    def click_test_connectivity(self):
        self.click_button(self.TEST_CONNECTIVITY)

    def assert_new_server_button_is_disabled(self):
        assert self.is_element_disabled_by_id(self.NEW_SERVER_BUTTON_ID)

    def click_new_server(self):
        self.click_button_by_id(self.NEW_SERVER_BUTTON_ID,
                                call_space=False,
                                should_scroll_into_view=False,
                                scroll_into_view_container=X_BODY)

    def click_advanced_settings(self):
        self.find_element_by_text('Advanced Settings').click()

    def save_advanced_settings(self):
        self.driver.find_element_by_css_selector(self.ADVANCED_SETTINGS_SAVE_BUTTON_CSS).click()

    def check_rt_adapter(self):
        self.driver.find_element_by_css_selector(self.RT_CHECKBOX_CSS).click()

    def assert_screen_is_restricted(self):
        self.switch_to_page()
        self.find_element_by_text('You do not have permission to access the Adapters screen')
        self.click_ok_button()

    def select_all_servers(self):
        self.driver.find_element_by_css_selector(self.DEVICE_CHECKBOX).click()

    def wait_for_server_green(self):
        self.wait_for_element_present_by_id(self.SERVER_GREEN_COLOR_ID)

    def wait_for_server_red(self):
        self.wait_for_element_present_by_id(self.SERVER_RED_COLOR_ID)

    def wait_for_adapter_green(self):
        self.wait_for_element_present_by_id(self.GREEN_COLOR_ID)

    def wait_for_adapter_red(self):
        self.wait_for_element_present_by_id(self.RED_COLOR_ID)

    def wait_for_adapter_orange(self):
        self.wait_for_element_present_by_id(self.ORANGE_COLOR_ID)

    def wait_for_connect_valid(self):
        self.wait_for_element_present_by_text(self.TEST_CONNECTIVITY_CONNECTION_IS_VALID)

    def wait_for_test_connectivity_not_supported(self):
        self.wait_for_element_present_by_text(self.TEST_CONNECTIVITY_NOT_SUPPORTED)

    def wait_for_problem_connecting_to_server(self):
        self.wait_for_element_present_by_text(self.TEST_CONNECTIVITY_PROBLEM)

    def clean_adapter_servers(self, name, delete_associated_entities=False):
        self.remove_server(None, name, delete_associated_entities=delete_associated_entities)

    def remove_server(self, ad_client=None, adapter_name=AD_NAME, adapter_search_field=AD_SERVER_SEARCH_FIELD,
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
            self.fill_text_by_element(element, value)

    def wait_for_data_collection_toaster_absent(self):
        self.wait_for_toaster_to_end(self.DATA_COLLECTION_TOASTER, retries=1200)

    def add_server(self, ad_client, adapter_name=AD_NAME):
        self.switch_to_page()
        self.wait_for_spinner_to_end()
        self.click_adapter(adapter_name)
        self.wait_for_spinner_to_end()
        self.click_new_server()

        dict_ = copy(ad_client)
        dict_.pop('use_ssl', None)
        dict_.pop('fetch_disabled_users', None)

        self.fill_creds(**dict_)
        self.click_save()
