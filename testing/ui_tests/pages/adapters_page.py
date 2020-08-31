import re
import time
from collections import namedtuple
from copy import copy
from datetime import datetime, timedelta
import pytest

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement

from axonius.utils.wait import wait_until
from test_credentials.json_file_credentials import (CLIENT_DETAILS_EXTRA,
                                                    FILE_NAME)
from test_credentials.json_file_credentials import client_details as json_file_creds
from test_helpers.file_mock_credentials import FileForCredentialsMock
from ui_tests.pages.entities_page import EntitiesPage
from ui_tests.pages.page import PAGE_BODY, SLEEP_INTERVAL, RETRY_WAIT_FOR_ELEMENT
from ui_tests.tests.ui_consts import (AD_ADAPTER_NAME,
                                      JSON_ADAPTER_NAME,
                                      CSV_NAME)


# NamedTuple doesn't need to be uppercase
# pylint: disable=C0103
Adapter = namedtuple('Adapter', 'name description')
TANIUM_ADAPTERS_CONNECTION_LABEL_UPDATED = '4250'


class AdaptersPage(EntitiesPage):
    ROOT_PAGE_CSS = 'li#adapters.x-nav-item'
    SEARCH_TEXTBOX_CSS = 'div.x-search-input > input.input-value'
    TABLE_ROW_CLASS = 'table-row'
    TABLE_CLASS = '.table'
    TEST_CONNECTIVITY = 'Check Network Connectivity'
    RT_CHECKBOX_CSS = '[for=realtime_adapter]+div'
    CUSTOM_DISCOVERY_ENABLE_CHECKBOX_CSS = '[for=enabled]+div'
    CUSTOM_CONNECTION_DISCOVERY_ENABLE_CHECKBOX_CSS = '.item_connection_discovery [for=enabled]+div'
    REPEAT_DAYS = 'repeat_every'
    CHECKBOX_CLASS = 'x-checkbox'
    CHECKED_CHECKBOX_CLASS = 'x-checkbox checked'
    ADVANCED_SETTINGS_SAVE_BUTTON_CSS = '.x-tab.active .configuration>.x-button'
    ADVANCED_SETTINGS_BUTTON_TEXT = 'Advanced Settings'

    CUSTOM_DISCOVERY_SCHEDULE_TIME_PICKER_INPUT_CSS = '.time-picker-text input'

    TEST_CONNECTIVITY_CONNECTION_IS_VALID = 'Connection is valid.'
    TEST_CONNECTIVITY_NOT_SUPPORTED = 'Test reachability is not supported for this adapter.'
    TEST_CONNECTIVITY_PROBLEM = 'Problem connecting'
    TEST_CREDENTIALS_PROBLEM = 'Failed to save connection details. ' \
                               'Changing connection details requires re-entering credentials'

    ERROR_ICON_CLASS = '.x-icon.icon-error'
    SUCCESS_ICON_CLASS = '.x-table-row:nth-child({position}) .x-icon.icon-success'
    ADAPTERS_SUCCESS_ICON_CLASS = '.adapters-table .table-row:nth-child({position}) .x-icon.icon-success'
    TYPE_ICON_CSS = '.x-icon.icon-{status_type}'
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
    INSTANCE_DROPDOWN_CSS_SELECTED = '#serverInstance div.trigger-text'
    INSTANCE_DROPDOWN_CSS = '.x-dropdown #serverInstance'

    CLIENT_DISCOVERY_CONFIGURATIONS_TAB = '//div[text()=\'Scheduling Configuration\']'
    CLIENT_DISCOVERY_CONFIGURATIONS_FORM_CSS = '.ant-tabs-content .discovery-configuration'
    CLIENT_DISCOVERY_ENABLED_CSS = '.discovery-configuration #enabled'

    INPUT_TYPE_PWD_VALUE = '********'

    CSV_ADAPTER_QUERY = 'adapters_data.csv_adapter.id == exists(true)'
    CSV_FILE_NAME = 'file_path'  # Changed by Alex A on Jan 27 2020 - because schema changed
    CSV_INPUT_ID = 'file_path'  # Changed by Alex A on Jan 27 2020 - because schema changed

    PASSWORD_VAULT_TOGGLE_CSS = '.provider-toggle'

    LAST_SEEN_THRESHOLD_HOURS = '21600'

    ADAPTER_INDICATOR_SUCCESS = 'success'
    ADAPTER_INDICATOR_ERROR = 'error'

    SAVE_AND_FETCH_BUTTON = 'Save and Fetch'
    CLOSE_ADAPTER_MODAL_CSS = '.config-server__close-icon-container'
    HELP_ICON_ADAPTER_MODAL_CSS = '.config-server .help-link'

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

    def click_save_and_fetch(self):
        self.get_enabled_button(self.SAVE_AND_FETCH_BUTTON).click()

    def is_save_button_disabled(self):
        return self.is_element_disabled(self.get_button(self.SAVE_AND_FETCH_BUTTON))

    def click_cancel(self):
        context_element = self.wait_for_element_present_by_css('.x-modal.config-server')
        self.driver.find_element_by_css_selector(self.CLOSE_ADAPTER_MODAL_CSS).click()

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
        self.wait_for_element_present_by_id('AdapterBase').click()
        time.sleep(1.5)

    def click_discovery_configuration(self):
        self.find_element_by_text('Discovery Configuration').click()
        time.sleep(1.5)

    def click_aws_advanced_configuration(self):
        self.find_element_by_text('AWS Configuration').click()
        time.sleep(1.5)

    def fill_schedule_date(self, text):
        self.fill_text_field_by_css_selector(self.CUSTOM_DISCOVERY_SCHEDULE_TIME_PICKER_INPUT_CSS, text)

    def check_custom_discovery_schedule(self):
        self.driver.find_element_by_css_selector(self.CUSTOM_DISCOVERY_ENABLE_CHECKBOX_CSS).click()

    def check_custom_connection_discovery_schedule(self):
        self.driver.find_element_by_css_selector(self.CUSTOM_CONNECTION_DISCOVERY_ENABLE_CHECKBOX_CSS).click()

    def change_custom_discovery_interval(self, days):
        self.fill_text_field_by_element_id(self.REPEAT_DAYS, days)

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

    def wait_for_server_red(self, retries=RETRY_WAIT_FOR_ELEMENT):
        self.wait_for_element_present_by_css(self.ERROR_ICON_CLASS, retries=retries)

    def wait_for_adapter_warning(self):
        self.wait_for_element_present_by_css(self.ERROR_ICON_CLASS)
        self.wait_for_element_present_by_css(self.WARNING_MARKER_CSS)

    def wait_for_connect_valid(self):
        self.wait_for_element_present_by_text(self.TEST_CONNECTIVITY_CONNECTION_IS_VALID)

    def wait_for_test_connectivity_not_supported(self):
        self.wait_for_element_present_by_text(self.TEST_CONNECTIVITY_NOT_SUPPORTED)

    def wait_for_problem_connecting_to_server(self):
        self.wait_for_element_present_by_text(self.TEST_CONNECTIVITY_PROBLEM, retries=600)

    def wait_for_credentials_problem_to_server(self):
        self.wait_for_element_present_by_text(self.TEST_CREDENTIALS_PROBLEM)

    def wait_for_problem_connecting_try_again(self, retries=RETRY_WAIT_FOR_ELEMENT, interval=SLEEP_INTERVAL):
        self.wait_for_element_present_by_text(
            self.TEXT_PROBLEM_CONNECTING_TRY_AGAIN,
            retries=retries,
            interval=interval)

    def clean_adapter_servers(self, name, delete_associated_entities=False):
        self.remove_server(None, name, delete_associated_entities=delete_associated_entities)

    def restore_json_client(self):
        self.clean_adapter_servers(JSON_ADAPTER_NAME, delete_associated_entities=True)
        self.add_json_server(json_file_creds, position=1, run_discovery_at_last=False)

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

        # Let's wait for the modal to be clickable properly
        time.sleep(1)

        self.approve_remove_selected()
        self.wait_for_elements_delete(expected_left=expected_left)

    def remove_json_extra_server(self, credentials, expected_left=1):
        self.remove_server(ad_client=credentials,
                           adapter_name=JSON_ADAPTER_NAME,
                           expected_left=expected_left,
                           delete_associated_entities=True,
                           adapter_search_field=self.JSON_FILE_SERVER_SEARCH_FIELD)

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

    def select_instance(self, instance):
        self.select_option_without_search(self.INSTANCE_DROPDOWN_CSS, self.DROPDOWN_SELECTED_OPTION_CSS, instance)

    def add_server(self, ad_client, adapter_name=AD_ADAPTER_NAME, instance=None):
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
        if instance:
            self.select_instance(instance)
        self.click_save_and_fetch()

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
            return self.driver.find_element_by_css_selector(self.HELP_ICON_ADAPTER_MODAL_CSS)
        except NoSuchElementException:
            return None

    def click_help_link(self):
        self.find_help_link().click()

    def find_status_symbol(self, status_type):
        return self.wait_for_element_present_by_css(self.TYPE_ICON_CSS.format(status_type=status_type))

    def find_status_symbol_success(self):
        return self.find_status_symbol(self.ADAPTER_INDICATOR_SUCCESS)

    def find_status_symbol_error(self):
        return self.find_status_symbol(self.ADAPTER_INDICATOR_ERROR)

    def find_status_count(self, status_type):
        element = self.wait_for_element_present_by_css(
            f'{self.TYPE_ICON_CSS.format(status_type=status_type)} ~ .summary_count')
        return int(element.text)

    def find_status_count_success(self):
        return self.find_status_count(self.ADAPTER_INDICATOR_SUCCESS)

    def find_status_count_error(self):
        return self.find_status_count(self.ADAPTER_INDICATOR_ERROR)

    def find_server_error(self):
        element = self.driver.find_element_by_css_selector(self.SERVER_ERROR_TEXT_CLASS)
        return element.text

    def get_adapters_table_length(self):
        adapters = self.get_adapter_list()
        return len(adapters)

    def click_configured_adapters_filter_switch(self):
        element = self.wait_for_element_present_by_css('.adapters-search .md-switch-thumb')
        element.click()

    def find_password_vault_button(self):
        return self.driver.find_element_by_css_selector(self.PASSWORD_VAULT_TOGGLE_CSS)

    def verify_password_vault_button_not_present(self):
        with pytest.raises(NoSuchElementException):
            self.find_password_vault_button()

    def find_password_vault_button_status(self):
        return self.driver.find_element_by_css_selector(f'{self.PASSWORD_VAULT_TOGGLE_CSS}__status')

    def get_configured_adapters_count_from_switch_label(self):
        pattern = r'configured only \((\d)\)'

        element = self.wait_for_element_present_by_css('.adapters-search .md-switch-label')
        element_text = element.text

        match_object = re.match(pattern, element_text, re.I | re.M)
        return int(match_object.group(1))

    def verify_only_configured_adapters_visible(self):
        adapters_count = self.get_adapters_table_length()
        configured_adapters_count = self.get_configured_adapters_count_from_switch_label()
        assert configured_adapters_count == adapters_count

    def create_new_adapter_connection(self, plugin_title: str, adapter_input: dict):
        self.wait_for_adapter(plugin_title)
        self.click_adapter(plugin_title)
        self.wait_for_table_to_load()
        self.click_new_server()
        self.fill_creds(**adapter_input)
        self.click_save_and_fetch()

    def get_instances_dropdown_selected_value(self):
        return self.driver.find_element_by_css_selector(self.INSTANCE_DROPDOWN_CSS_SELECTED).text

    def connect_adapter(self, adapter_name, server_details, position=1, instance=None):
        self.wait_for_adapter(adapter_name)
        self.add_server(ad_client=server_details, adapter_name=adapter_name, instance=instance)
        self.wait_for_server_green(position=position)
        self.wait_for_data_collection_toaster_absent()
        self.switch_to_page()

    def add_json_server(self, server_details, position=2, run_discovery_at_last=True, instance=None):
        self.connect_adapter(adapter_name=JSON_ADAPTER_NAME, server_details=server_details,
                             position=position, instance=instance)
        self.click_adapter(adapter_name=JSON_ADAPTER_NAME)
        self.wait_for_table_to_be_responsive()
        self.click_advanced_settings()
        self.fill_last_seen_threshold_hours(self.LAST_SEEN_THRESHOLD_HOURS)
        self.save_advanced_settings()
        self.wait_for_spinner_to_end()
        self.switch_to_page()
        if run_discovery_at_last:
            # now it is useless, but in the long future could prove useful
            self.test_base.base_page.run_discovery()

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
        self.wait_for_element_present_by_id(element_id='connectionLabel', retries=3)
        self.fill_creds(connectionLabel=connection_label)
        self.click_save_and_fetch()

    def upload_csv(self, csv_file_name, csv_data, is_user_file=False, wait_for_toaster=False):
        self.open_add_edit_server(CSV_NAME)
        self.fill_upload_csv_form_with_csv(csv_file_name, csv_data, is_user_file)
        self.click_save_and_fetch()
        if wait_for_toaster:
            self.wait_for_data_collection_toaster_start()
            self.wait_for_data_collection_toaster_absent()

    def fill_upload_csv_form_with_csv(self, csv_file_name, csv_data=None, is_user_file=False):
        if csv_data is None:
            csv_data = {}
        self.upload_file_by_id(self.CSV_INPUT_ID, csv_data[csv_file_name].file_contents)
        credentials = {
            **csv_data,
            'user_id': csv_file_name,
            'connectionLabel': csv_file_name,
        }
        if credentials.get(csv_file_name, None):
            credentials.pop(csv_file_name)
        self.fill_creds(**credentials)
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

    def click_vault_button(self):
        self.find_password_vault_button().click()
        # wait for vault popup by sync on fetch button
        self.wait_for_element_present_by_id(element_id='secret', retries=5)

    def check_vault_fetch_status(self, should_succeed=True) -> bool:
        try:
            password_vault_icon_status = self.find_password_vault_button_status()
            class_attribute = 'success' if should_succeed else 'error'
            return class_attribute in password_vault_icon_status.get_attribute('class')
        except NoSuchElementException:
            return False

    def check_vault_passsword_success_status(self) -> bool:
        return self.check_vault_fetch_status(should_succeed=True)

    def check_vault_passsword_failure_status(self) -> bool:
        return self.check_vault_fetch_status(should_succeed=False)

    def fetch_password_from_thycotic_vault(self, secret_id: str, vault_field: str = None, is_negative_test=False):
        wait_until(self.find_password_vault_button,
                   check_return_value=True,
                   tolerated_exceptions_list=[NoSuchElementException])
        self.click_vault_button()

        self.fill_text_field_by_element_id('secret', secret_id)
        if vault_field:
            self.fill_text_field_by_element_id('field', vault_field)
        self.click_button('Fetch')
        time.sleep(1)
        if is_negative_test:
            wait_until(self.check_vault_passsword_failure_status, check_return_value=True, total_timeout=30)
        else:
            wait_until(self.check_vault_passsword_success_status, check_return_value=True, total_timeout=30)

    def find_server_connection_label_value(self):
        return self.driver.find_element_by_id('connectionLabel').get_attribute('value')

    def update_server_connection_label(self, adapter_name, field_name, field_value, update_label):
        # find adapter client by matching connection label, useful when having multiple
        # clients and index is unkown. once match update the connection label value
        self.wait_for_adapter(adapter_name)
        self.click_adapter(adapter_name)
        self.wait_for_spinner_to_end()
        self.wait_for_table_to_load()
        self.click_specific_row_by_field_value(field_name=field_name, field_value=field_value)
        self.wait_for_element_present_by_id(element_id='connectionLabel', retries=5)
        self.fill_creds(connectionLabel=update_label)
        self.click_save_and_fetch()
        self.wait_for_data_collection_toaster_start()
        self.wait_for_data_collection_toaster_absent()

    def update_json_file_server_connection_label(self, client_name, update_label):
        self.update_server_connection_label(JSON_ADAPTER_NAME, 'Name', client_name, update_label)

    def update_csv_connection_label(self, file_name, update_label):
        self.update_server_connection_label(CSV_NAME, 'File name', file_name, update_label)

    @staticmethod
    def set_discovery_time(minutes):
        current_utc = datetime.utcnow()
        timepicker_input = current_utc + timedelta(minutes=minutes)
        return timepicker_input.time().strftime('%I:%M%p').lower()

    def toggle_adapters_discovery_configurations(self, adapter_name, discovery_time=None, discovery_interval=None,
                                                 toggle_connection=False):
        self.switch_to_page()
        self.wait_for_spinner_to_end()
        self.click_adapter(adapter_name)
        self.wait_for_spinner_to_end()
        self.wait_for_table_to_load()
        self.click_advanced_settings()
        time.sleep(1.5)
        self.click_discovery_configuration()
        self.check_custom_discovery_schedule()
        if toggle_connection:
            self.check_custom_connection_discovery_schedule()

        if discovery_time and discovery_interval:
            self.fill_schedule_date(self.set_discovery_time(2))
            self.change_custom_discovery_interval(1)
        self.save_advanced_settings()

    def toggle_adapters_connection_discovery(self, adapter_name):
        self.switch_to_page()
        self.wait_for_spinner_to_end()
        self.click_adapter(adapter_name)
        self.wait_for_spinner_to_end()
        self.wait_for_table_to_load()
        self.click_advanced_settings()
        time.sleep(1.5)
        self.click_discovery_configuration()
        self.check_custom_connection_discovery_schedule()
        time.sleep(1)
        self.save_advanced_settings()

    def toggle_adapter_client_connection_discovery(self, adapter_name, client_position, discovery_time,
                                                   discovery_interval):
        self.switch_to_page()
        self.wait_for_spinner_to_end()
        self.click_adapter(adapter_name)
        self.wait_for_spinner_to_end()
        self.wait_for_table_to_load()
        self.click_edit_server(client_position)
        self.wait_for_element_present_by_xpath(self.CLIENT_DISCOVERY_CONFIGURATIONS_TAB)
        self.driver.find_element_by_xpath(self.CLIENT_DISCOVERY_CONFIGURATIONS_TAB).click()
        self.wait_for_element_present_by_css(self.CLIENT_DISCOVERY_CONFIGURATIONS_FORM_CSS)
        time.sleep(1)
        self.driver.find_element_by_css_selector(self.CLIENT_DISCOVERY_ENABLED_CSS).click()
        time.sleep(1)

        if discovery_time and discovery_interval:
            self.fill_schedule_date(self.set_discovery_time(2))
            self.change_custom_discovery_interval(1)

        self.click_save_and_fetch()
