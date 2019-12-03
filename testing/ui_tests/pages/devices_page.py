import re
import time

import pytest
from selenium.common.exceptions import NoSuchElementException

from axonius.utils.wait import wait_until

from ui_tests.pages.entities_page import EntitiesPage


class DevicesPage(EntitiesPage):
    FIELD_NETWORK_INTERFACES_IPS = 'Network Interfaces: IPs'
    FIELD_NETWORK_INTERFACES_MAC = 'Network Interfaces: Mac'
    FIELD_NETWORK_INTERFACES = 'Network Interfaces'
    FIELD_NETWORK_INTERFACES_NAME = 'network_interfaces'
    FIELD_IPS = 'IPs'
    FIELD_IPS_NAME = 'ips'
    FIELD_MAC = 'Mac'
    FIELD_MAC_NAME = 'mac'
    FIELD_NETWORK_INTERFACES_SUBNETS = 'Network Interfaces: Subnets'
    FIELD_SUBNETS = 'Subnets'
    FIELD_NETWORK_INTERFACES_VLANS = 'Network Interfaces: Vlans'
    FIELD_VLANS_VLAN_NAME = 'Vlans: Vlan Name'
    FIELD_VLANS_TAG_ID = 'Vlans: Tag ID'
    FIELD_VLAN_NAME = 'Vlan Name'
    FIELD_USERS = 'Users'
    FIELD_USERS_NAME = 'users'
    FIELD_SID_NAME = 'user_sid'
    FIELD_USERS_LAST_USE = 'Last Use Time'
    FIELD_USERS_LAST_USE_NAME = 'last_use_date'
    FIELD_LAST_USED_USERS = 'Last Used Users'
    FIELD_FIRST_FETCH_TIME = 'First Fetch Time'
    FIELD_USERS_LOCAL = 'Is Local'
    FIELD_USERS_LOCAL_NAME = 'is_local'
    FIELD_USERS_USERNAME = 'Users: Username'
    FIELD_CONNECTED_DEVICES = 'Connected Devices'
    FIELD_CONNECTED_DEVICES_NAME = 'Connected Devices: Remote Device Name'
    FIELD_REMOTE_NAME = 'Remote Device Name'
    FIELD_TAG_ID = 'Tag ID'
    FIELD_OS_TYPE = 'OS: Type'
    FIELD_OS_MAJOR = 'OS: Major'
    FIELD_OS_BUILD = 'OS: Build'
    FIELD_OS_BITNESS = 'OS: Bitness'
    FIELD_CPU_BITNESS = 'CPUs: Bitness'
    FIELD_AGENT_VERSION = 'Agent Version'
    FIELD_PORT_ACCESS_PORT_TYPE = 'Port Access: Port Type'
    FIELD_PART_OF_DOMAIN = 'Part Of Domain'
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
    VALUE_SAVED_QUERY_LINUX = 'Linux Operating System'
    VALUE_OS_WINDOWS = 'Windows'
    TAG_MODAL_CSS = '.x-tag-modal'
    TAG_CHECKBOX_CSS = f'{TAG_MODAL_CSS} .x-checkbox-list .x-checkbox'
    TAGS_TEXTBOX_CSS = f'{TAG_MODAL_CSS} .x-search-input .input-value'
    TAGGING_X_DEVICE_MESSAGE = 'Tagged {number} devices!'
    MULTI_LINE_CSS = 'div.x-data-table.multiline'
    FILTER_HOSTNAME = 'specific_data.data.hostname == regex("{filter_value}", "i")'
    ENFORCEMENT_DIALOG_DROPDOWN_CSS = 'div.x-select-trigger'
    QUERY_FIELD_VALUE = '.x-select-typed-field .x-dropdown.x-select.field-select'

    DELETE_DIALOG_TEXT_REGEX = 'You are about to delete \\d+ devices\\.'

    BASIC_INFO_FIELD_XPATH = '//div[contains(@class, \'x-tab active\')]//div[contains(@class, \'x-tab active\')]' \
                             '//div[preceding-sibling::label[text()=\'{field_title}\']]'

    @property
    def url(self):
        return f'{self.base_url}/devices'

    @property
    def root_page_css(self):
        return 'li#devices.x-nav-item'

    def click_tag_save_button(self):
        self.click_button(self.SAVE_BUTTON, context=self.driver.find_element_by_css_selector(self.TAG_MODAL_CSS))

    def check_if_table_is_multi_line(self):
        self.wait_for_element_present_by_css(self.MULTI_LINE_CSS)

    def check_if_adapter_tab_not_exist(self):
        with pytest.raises(NoSuchElementException):
            self.driver.find_element_by_css_selector('#specific')

    def wait_for_success_tagging_message(self, number=1):
        message = self.FEEDBACK_MODAL_MESSAGE_XPATH.format(message=self.TAGGING_X_DEVICE_MESSAGE.format(number=number))
        self.wait_for_element_present_by_xpath(message)
        self.wait_for_element_absent_by_xpath(message)

    def open_enforce_dialog(self):
        self.click_button('Actions', partial_class=True, should_scroll_into_view=False)
        self.click_actions_enforce_button()

    def enforce_action_on_query(self, query, action):
        self.run_filter_query(query)
        self.select_all_current_page_rows_checkbox()
        self.open_enforce_dialog()
        self.select_option_without_search(
            self.ENFORCEMENT_DIALOG_DROPDOWN_CSS,
            self.DROPDOWN_SELECTED_OPTION_CSS, action
        )
        self.click_button('Run')
        time.sleep(1.5)  # wait for run to fade away

    def open_tag_dialog(self):
        self.click_button('Actions', partial_class=True, should_scroll_into_view=False)
        self.click_actions_tag_button()

    def add_new_tag(self, tag_text, number=1):
        self.open_tag_dialog()
        self.create_save_tag(tag_text, number)
        self.wait_for_table_to_load()

    def create_save_tag(self, tag_text, number=1):
        self.fill_text_field_by_css_selector(self.TAGS_TEXTBOX_CSS, tag_text)
        self.wait_for_element_present_by_css(self.TAG_CHECKBOX_CSS).click()
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

    def get_first_fetch_time(self):
        return self.driver.find_element_by_css_selector(
            '[format="date-time"] > label[for="first_fetch_time"] + div').text

    def create_saved_query(self, data_query, query_name):
        self.switch_to_page()
        self.reset_query()
        self.fill_filter(data_query)
        self.enter_search()
        self.click_save_query()
        self.fill_query_name(query_name)
        self.click_save_query_save_button()

    def get_value_for_label_in_device_page(self, label_text):
        text = self.driver.find_element_by_xpath(self.DIV_BY_LABEL_TEMPLATE.format(label_text=label_text)).text
        return text.split('\n')[1]  # [0] is the label itself

    def add_query_last_seen(self):
        self.click_query_wizard()
        self.add_query_expression()
        expressions = self.find_expressions()
        self.select_query_logic_op(self.QUERY_LOGIC_AND, parent=expressions[1])
        self.select_query_field(self.FIELD_LAST_SEEN, parent=expressions[1])
        self.select_query_comp_op('days', parent=expressions[1])
        self.fill_query_value(5, parent=expressions[1])
        self.wait_for_table_to_load()
        self.close_dropdown()

    def run_enforcement_on_selected_device(self, enforcement_name):
        self.open_enforce_dialog()
        self.select_option_without_search(dropdown_css_selector=self.ENFORCEMENT_DIALOG_DROPDOWN_CSS,
                                          selected_options_css_selector=self.DROPDOWN_SELECTED_OPTION_CSS,
                                          text=enforcement_name)
        self.click_button('Run')
        time.sleep(1.5)  # wait for run to fade away

    def find_general_data_table_link(self, table_title):
        self.click_row()
        self.wait_for_spinner_to_end()
        self.click_general_tab()
        self.click_tab(table_title)
        return self.driver.find_element_by_css_selector('.x-entity-general .x-tab.active .x-table .x-table-row td a')

    def find_general_data_basic_link(self, field_title):
        self.click_row()
        self.wait_for_spinner_to_end()
        self.click_general_tab()
        # Wait while animation of list expansion
        time.sleep(1)
        field_el = self.find_element_by_xpath(self.BASIC_INFO_FIELD_XPATH.format(field_title=field_title))
        return field_el.find_element_by_css_selector('.item .object')
