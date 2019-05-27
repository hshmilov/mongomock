import re

import pytest
from selenium.common.exceptions import NoSuchElementException

from axonius.utils.wait import wait_until

from ui_tests.pages.entities_page import EntitiesPage


class DevicesPage(EntitiesPage):
    FIELD_NETWORK_INTERFACES_IPS = 'Network Interfaces: IPs'
    FIELD_NETWORK_INTERFACES_MAC = 'Network Interfaces: Mac'
    FIELD_NETWORK_INTERFACES = 'Network Interfaces'
    FIELD_IPS = 'IPs'
    FIELD_MAC = 'Mac'
    FIELD_NETWORK_INTERFACES_SUBNETS = 'Network Interfaces: Subnets'
    FIELD_SUBNETS = 'Subnets'
    FIELD_NETWORK_INTERFACES_VLANS = 'Network Interfaces: Vlans'
    FIELD_VLANS_VLAN_NAME = 'Vlans: Vlan Name'
    FIELD_VLANS_TAG_ID = 'Vlans: Tag ID'
    FIELD_VLAN_NAME = 'Vlan Name'
    FIELD_USERS = 'Users'
    FIELD_USERS_LAST_USE = 'Last Use Time'
    FIELD_TAG_ID = 'Tag ID'
    FIELD_OS_TYPE = 'OS: Type'
    FIELD_TAGS = 'Tags'
    FIELD_ADAPTERS = 'Adapters'
    FIELD_LAST_SEEN = 'Last Seen'
    FIELD_HOSTNAME_TITLE = 'Host Name'
    FIELD_HOSTNAME_NAME = 'hostname'
    FIELD_ASSET_NAME = 'Asset Name'
    FIELD_SAVED_QUERY = 'Saved Query'
    FIELD_AVSTATUS = 'AvStatus'
    FIELD_AD_NAME = 'AD name'
    FIELD_INSTALLED_SOFTWARE = 'Installed Software'
    FIELD_INSTALLED_SOFTWARE_NAME = 'Name'
    FIELD_INSTALLED_SOFTWARE_VERSION = 'Version'
    VALUE_SAVED_QUERY_WINDOWS = 'Windows Operating System'
    VALUE_SAVED_QUERY_LINUX = 'Linux Operating System'
    VALUE_OS_WINDOWS = 'Windows'
    TAG_CHECKBOX_CSS = 'div.modal-container.w-xl > div.modal-body > div > div.x-checkbox-list > div > div'
    TAG_SAVE_BUTTON_CSS = 'div.modal-container.w-xl > div.modal-footer > div > button:nth-child(2)'
    LABELS_TEXTBOX_CSS = 'div.modal-body > div > div.x-search-input > input'
    TAGGING_X_DEVICE_MESSAGE = 'Tagged {number} devices!'
    TAGGING_X_DEVICE_XPATH = './/div[contains(@class, \'t-center\') and .//text()=\'{message}\']'
    MULTI_LINE_CSS = 'div.x-data-table.multiline'
    FILTER_HOSTNAME = 'specific_data.data.hostname == regex("{filter_value}", "i")'

    DELETE_DIALOG_TEXT_REGEX = 'You are about to delete \\d+ devices\\.'

    @property
    def url(self):
        return f'{self.base_url}/devices'

    @property
    def root_page_css(self):
        return 'li#devices.x-nav-item'

    def click_tag_save_button(self):
        self.driver.find_element_by_css_selector(self.TAG_SAVE_BUTTON_CSS).click()

    def check_if_table_is_multi_line(self):
        self.wait_for_element_present_by_css(self.MULTI_LINE_CSS)

    def check_if_adapter_tab_not_exist(self):
        with pytest.raises(NoSuchElementException):
            self.driver.find_element_by_css_selector('#specific')

    def wait_for_success_tagging_message(self, number=1):
        message = self.TAGGING_X_DEVICE_XPATH.format(message=self.TAGGING_X_DEVICE_MESSAGE.format(number=number))
        self.wait_for_element_present_by_xpath(message)
        self.wait_for_element_absent_by_xpath(message)

    def open_tag_dialog(self):
        self.click_button('Actions', partial_class=True, should_scroll_into_view=False)
        self.click_actions_tag_button()

    def add_new_tag(self, tag_text, number=1):
        self.open_tag_dialog()
        self.create_save_tag(tag_text, number)

    def create_save_tag(self, tag_text, number=1):
        self.fill_text_field_by_css_selector(self.LABELS_TEXTBOX_CSS, tag_text)
        self.wait_for_element_present_by_css(self.TAG_CHECKBOX_CSS).click()
        self.click_tag_save_button()
        self.wait_for_success_tagging_message(number)
        self.wait_for_spinner_to_end()

    def remove_first_tag(self):
        self.open_tag_dialog()
        self.wait_for_element_present_by_css(self.TAG_CHECKBOX_CSS).click()
        self.click_tag_save_button()
        self.wait_for_success_tagging_message()

    def remove_tag(self, text):
        self.open_tag_dialog()
        self.find_element_by_text(text).click()
        self.click_tag_save_button()
        self.wait_for_success_tagging_message()

    def get_first_tag_text(self):
        return self.get_first_row_tags().splitlines()[0]

    def get_first_row_tags(self):
        return self.driver.find_elements_by_css_selector(self.TABLE_FIRST_ROW_TAG_CSS)[0].text

    def assert_screen_is_restricted(self):
        self.switch_to_page_allowing_failure()
        self.find_element_by_text('You do not have permission to access the Devices screen')
        self.click_ok_button()

    def query_hostname_contains(self, string):
        self.run_filter_query(self.FILTER_HOSTNAME.format(filter_value=string))

    def delete_devices(self, query_filter=None):
        """
        By default removes the json device after querying it.
        :param query_filter: Can delete any device by query filter
        """
        self.switch_to_page()
        if query_filter:
            self.run_filter_query(query_filter)
        else:
            self.clear_filter()
        self.wait_for_table_to_load()
        if query_filter:
            self.click_row_checkbox()
        else:
            self.select_all_current_page_rows_checkbox()
            self.click_select_all_entities()
        self.open_delete_dialog()
        wait_until(lambda: re.match(self.DELETE_DIALOG_TEXT_REGEX, self.read_delete_dialog()) is not None)
        self.confirm_delete()
        wait_until(lambda: not self.count_entities())

    def get_fetch_time(self):
        return self.driver.find_element_by_css_selector('[format="date-time"] > label[for="fetch_time"] + div').text

    def create_saved_query(self, data_query, query_name):
        self.switch_to_page()
        self.fill_filter(data_query)
        self.enter_search()
        self.click_save_query()
        self.fill_query_name(query_name)
        self.click_save_query_save_button()
