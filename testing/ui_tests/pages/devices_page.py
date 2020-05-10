import re
import time
import pytest
from retrying import retry
from selenium.common.exceptions import NoSuchElementException

from axonius.consts.gui_consts import ADAPTER_CONNECTIONS_FIELD
from axonius.utils.wait import wait_until

from ui_tests.pages.entities_page import EntitiesPage


class DevicesPage(EntitiesPage):
    FIELD_NETWORK_INTERFACES_MAC = 'Network Interfaces: MAC'
    FIELD_NETWORK_INTERFACES_IPS = 'Network Interfaces: IPs'
    FIELD_NETWORK_INTERFACES_PORT = 'Network Interfaces: Port'
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
    FIELD_FIRST_SEEN = 'First Seen'
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
    FIELD_ADAPTER_TAGS = 'Adapter Tags'
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
    FIELD_FIREWALL_RULES_FROM_PORT = 'Firewall Rules: From port'
    FIELD_ADAPTER_CONNECTION_LABEL = 'Adapter Connection Label'
    PREFERRED_FIELDS = ['Preferred Host Name', 'Preferred OS Type', 'Preferred OS Distribution',
                        'Preferred MAC Address', 'Preferred IPs']
    VALUE_OS_WINDOWS = 'Windows'
    TAGGING_X_DEVICE_MESSAGE = 'Tagged {number} devices!'
    MULTI_LINE_CSS = 'div.x-data-table.multiline'
    FILTER_HOSTNAME = 'specific_data.data.hostname == regex("{filter_value}", "i")'
    FILTER_OS = 'specific_data.data.os.type == "{os}"'
    UNMANAGED_QUERY = 'not (specific_data.data.adapter_properties == \"Agent\") ' \
                      'and not (specific_data.data.adapter_properties == \"Manager\")'
    FILTER_OS_WINDOWS = FILTER_OS.format(os='Windows')
    FILTER_OS_LINUX = FILTER_OS.format(os='Linux')
    ENFORCEMENT_DIALOG_DROPDOWN_CSS = 'div.x-select-trigger'
    QUERY_FIELD_VALUE = '.x-select-typed-field .x-dropdown.x-select.field-select'
    DELETE_DIALOG_TEXT_REGEX = 'You are about to delete \\d+ devices\\.'
    BASIC_INFO_FIELD_XPATH = '//div[contains(@class, \'x-tab active\')]//div[contains(@class, \'x-tab active\')]' \
                             '//div[preceding-sibling::label[normalize-space(text())=\'{field_title}\']]'
    TAG_COMBOBOX_CSS = '.x-combobox_results-card--keep-open.v-card'
    SPECIFIC_SEARCH_DROPDOWN_ITEM_XPATH = '//div[@id=\'specific_search_select\']' \
                                          '//div[contains(text(),\'{query_name_text}\')]'
    SPECIFIC_SEARCH_CLOSE_BUTTON_CSS = '.search-input-badge__remove'
    SPECIFIC_SEARCH_DROPDOWN_CONTENT_CSS = '#specific_search_select .menu-content .x-menu-item'
    AD_PREDEFINED_QUERY_NAME = 'Devices seen in last 7 days'

    PartialState = {
        'PARTIAL': 'mixed',
        'CHECKED': 'true',
        'UNCHECKED': 'false'
    }
    PartialIcon = {
        'PARTIAL': 'checkbox--partial',
        'CHECKED': 'checkbox--checked',
        'UNCHECKED': 'checkbox--unchecked'
    }

    SYSTEM_DEFAULT_FIELDS = [ADAPTER_CONNECTIONS_FIELD,
                             FIELD_ASSET_NAME, FIELD_HOSTNAME_TITLE, FIELD_LAST_SEEN,
                             FIELD_NETWORK_INTERFACES_MAC, FIELD_NETWORK_INTERFACES_IPS,
                             FIELD_OS_TYPE, EntitiesPage.FIELD_TAGS]

    @property
    def url(self):
        return f'{self.base_url}/devices'

    @property
    def root_page_css(self):
        return 'li#devices.x-nav-item'

    def check_if_table_is_multi_line(self):
        self.wait_for_element_present_by_css(self.MULTI_LINE_CSS)

    def check_if_adapter_tab_not_exist(self):
        with pytest.raises(NoSuchElementException):
            self.driver.find_element_by_css_selector('#specific')

    def open_enforce_dialog(self):
        self.open_actions_menu()
        self.click_actions_enforce_button()

    def enforce_action_on_query(self, query, action):
        self.run_filter_query(query)
        self.toggle_select_all_rows_checkbox()
        self.open_enforce_dialog()
        self.select_option_without_search(
            self.ENFORCEMENT_DIALOG_DROPDOWN_CSS,
            self.DROPDOWN_SELECTED_OPTION_CSS, action
        )
        self.click_button('Run')
        time.sleep(1.5)  # wait for run to fade away

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
            self.toggle_select_all_rows_checkbox()
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

    def get_value_for_label_in_device_page(self, label_text):
        text = self.driver.find_element_by_xpath(self.DIV_BY_LABEL_TEMPLATE.format(label_text=label_text)).text
        return text.split('\n')[1]  # [0] is the label itself

    def _add_query_last_seen(self, query_comp_day):
        self.click_query_wizard()
        self.add_query_expression()
        expressions = self.find_expressions()
        self.select_query_logic_op(self.QUERY_LOGIC_AND, parent=expressions[1])
        self.select_query_field(self.FIELD_LAST_SEEN, parent=expressions[1])
        self.select_query_comp_op(query_comp_day, parent=expressions[1])
        self.fill_query_value(5, parent=expressions[1])
        self.wait_for_table_to_load()
        self.close_dropdown()

    def add_query_last_seen_last_day(self):
        self._add_query_last_seen(self.QUERY_COMP_DAYS)

    def add_query_last_seen_next_day(self):
        self._add_query_last_seen(self.QUERY_COMP_NEXT_DAYS)

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

    @staticmethod
    def is_tag_has_status(tag, status):
        return tag.find_element_by_css_selector('.checkbox--{}'.format(status)).is_displayed()

    def assert_csv_field_with_search(self, search_text):
        self.fill_enter_table_search(search_text)
        self.assert_csv_field_match_ui_data(self.generate_csv_field(
            'devices',
            self.driver.current_url.split('/')[-1],
            self.FIELD_NETWORK_INTERFACES_NAME,
            self.FIELD_MAC_NAME,
            search_text=search_text
        ))

    def check_search_text_result(self, text):
        self.wait_for_table_to_load()
        all_data = self.get_all_data()
        assert len(all_data)
        assert any(text in x for x in all_data)

    def check_search_text_result_in_column(self, text, column_name):
        self.wait_for_table_to_load()
        all_data = self.get_all_data_proper()
        column_data = [x[column_name] for x in all_data]
        assert len(column_data)
        assert all(text in x.lower() for x in column_data)

    def find_specific_search_badge(self):
        return self.driver.find_element_by_css_selector(self.SPECIFIC_SEARCH_CLOSE_BUTTON_CSS)

    def close_specific_search_badge(self):
        self.find_specific_search_badge().click()

    @retry(wait_fixed=500, stop_max_attempt_number=30)
    def select_specific_search_by_name(self, query_name):
        el = self.wait_for_element_present_by_xpath(
            self.SPECIFIC_SEARCH_DROPDOWN_ITEM_XPATH.format(query_name_text=query_name))
        el.click()

    def get_specific_search_list(self):
        return [x.text for x in self.driver.find_elements_by_css_selector(self.SPECIFIC_SEARCH_DROPDOWN_CONTENT_CSS)]

    def select_specific_search(self, name):
        self.open_search_list()
        self.select_specific_search_by_name(name)
        self.wait_for_table_to_load()

    def search(self, value):
        self.fill_filter(value)
        self.enter_search()
        self.wait_for_table_to_load()

    def find_save_as_user_search_default_button(self, search_name=''):
        if search_name:
            return self.find_element_by_text(self.SAVE_AS_USER_SEARCH_DEFAULT.format(search_name=search_name))
        return self.find_element_by_text(self.SAVE_AS_USER_DEFAULT)

    def find_reset_columns_to_user_default_button(self, search=False):
        if search:
            return self.find_element_by_text(self.RESET_COLS_USER_SEARCH_DEFAULT_TEXT)
        return self.find_element_by_text(self.RESET_COLS_USER_DEFAULT_TEXT)

    def find_reset_columns_to_system_default_button(self, search=False):
        if search:
            return self.find_element_by_text(self.RESET_COLS_SYSTEM_SEARCH_DEFAULT_TEXT)
        return self.find_element_by_text(self.RESET_COLS_SYSTEM_DEFAULT_TEXT)

    def wait_for_success_tagging_message(self, number=1):
        self.wait_for_success_tagging_message_for_entities(number, self.TAGGING_X_DEVICE_MESSAGE)

    def query_tanium_connection_label(self, tanium_client: dict) -> int:
        self.switch_to_page()
        self.wait_for_table_to_load()
        self.click_query_wizard()
        self.select_query_filter(attribute=self.FIELD_ADAPTER_CONNECTION_LABEL,
                                 operator='equals',
                                 value=tanium_client['connection_label'],
                                 clear_filter=True)
        self.wait_for_table_to_load()
        return self.count_entities()

    def add_query_last_seen_in_days(self, days):
        self.click_query_wizard()
        expressions = self.find_expressions()
        self.select_query_field(self.FIELD_LAST_SEEN, parent=expressions[0])
        self.select_query_comp_op(self.QUERY_COMP_DAYS, parent=expressions[0])
        self.fill_query_value(days, parent=expressions[0])
        self.wait_for_table_to_load()
        self.close_dropdown()
