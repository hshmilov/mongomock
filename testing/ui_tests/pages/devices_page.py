import re
import time
import pytest
from retrying import retry
from selenium.common.exceptions import NoSuchElementException

from axonius.consts.gui_consts import ADAPTER_CONNECTIONS_FIELD, ActionCategory, Action
from axonius.utils.wait import wait_until
from test_credentials.test_gui_credentials import DEFAULT_USER

from ui_tests.pages.entities_page import EntitiesPage, CSV_TIMEOUT
from ui_tests.tests.ui_consts import (CSV_ADAPTER_FILTER, AWS_ADAPTER_FILTER, COMP_DAYS, COMP_NEXT_DAYS, LOGIC_AND,
                                      COMP_EQUALS, COMP_IN)


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
    FIELD_FETCH_TIME = 'Fetch Time'
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
    FIELD_OS_DISTRIBUTION = 'OS: Distribution'
    FIELD_CPU_BITNESS = 'CPUs: Bitness'
    FIELD_AGENT_VERSION = 'Agent Version'
    FIELD_PORT_ACCESS_PORT_TYPE = 'Port Access: Port Type'
    FIELD_PART_OF_DOMAIN = 'Part Of Domain'
    FIELD_TAGS = 'Tags'
    FIELD_ADAPTER_TAGS = 'Adapter Tags'
    FIELD_ADAPTER_PROPERTIES = 'Adapter Properties'
    FIELD_LAST_SEEN = 'Last Seen'
    FIELD_ADAPTER_CONNECTIONS = 'Adapter Connections'
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
    FIELD_VULNERABLE_SOFTWARE = 'Vulnerable Software'
    PREFERRED_HOSTNAME_FIELD = 'Preferred Host Name'
    AGENT_VERSIONS_FIELD = 'Agent Versions'
    AGENT_VERSIONS_NAME_FIELD = 'Agent Versions: Name'
    PREFERRED_FIELDS = [PREFERRED_HOSTNAME_FIELD, 'Preferred OS Type', 'Preferred OS Distribution',
                        'Preferred MAC Address', 'Preferred IPs']
    VALUE_OS_WINDOWS = 'Windows'
    TAGGING_X_DEVICE_MESSAGE = 'Tagged {number} devices!'
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
    HOST_NAME_AGGREGATED_FIELD_CSS = '.x-list .item-container .label[for="specific_data.data.hostname"] ~ div .item'
    ENFORCEMENT_PANEL_CONTENT_CSS = '.enforcement-panel.x-side-panel .ant-drawer-body .ant-drawer-body__content'
    SAVE_AND_RUN_ENFORCEMENT_BUTTON = 'Save and Run'
    BACK_TO_ACTION_LIBRARY_BUTTON_CSS = '.back-button'
    ENFORCEMENT_PANEL_FOOTER_ERROR_CSS = '.error-text'
    ENFORCEMENT_TASK_SUCCESS_MESSAGE = 'Enforcement task has been created successfully'
    ENFORCEMENT_RESULT_LINK_XPATH = '//div[contains(@class, \'navigate-task-link\')]' \
                                    '/a[normalize-space(text())=\'Enforcement task has been created successfully\']'

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

    def check_if_adapter_tab_not_exist(self):
        with pytest.raises(NoSuchElementException):
            self.driver.find_element_by_css_selector('#specific')

    def open_enforce_dialog(self):
        self.open_actions_menu()
        self.click_actions_enforce_button(self.TABLE_ACTIONS_RUN_ENFORCE)
        time.sleep(0.5)

    def open_enforcement_panel(self):
        self.open_actions_menu()
        self.click_actions_enforce_button(self.TABLE_ACTIONS_ADD_ENFORCE)
        self.wait_for_element_present_by_css(self.ENFORCEMENT_PANEL_CONTENT_CSS, is_displayed=True)
        # the autofocus has debounce for 500 ms.
        time.sleep(0.6)

    def open_action_tag_config(self):
        self.find_element_by_text(ActionCategory.Utils).click()
        self.find_element_by_text(Action.tag.value).click()

    def go_back_to_action_library(self):
        self.driver.find_element_by_css_selector(self.BACK_TO_ACTION_LIBRARY_BUTTON_CSS).click()

    def get_enforcement_result_link(self):
        return self.find_element_by_xpath(self.ENFORCEMENT_RESULT_LINK_XPATH)

    def get_save_and_run_enforcement_button(self):
        return self.get_button(self.SAVE_AND_RUN_ENFORCEMENT_BUTTON)

    def is_enforcement_panel_save_button_disabled(self):
        return self.is_element_disabled(self.get_save_and_run_enforcement_button())

    def fill_enforcement_action_name(self, action_name):
        self.fill_text_field_by_element_id(self.ACTION_NAME_ID, action_name)

    def get_enforcement_name(self):
        return self.driver.find_element_by_id(self.ENFORCEMENT_NAME_ID).text

    def get_enforcement_panel_error(self):
        return self.driver.find_element_by_css_selector(self.ENFORCEMENT_PANEL_FOOTER_ERROR_CSS).text

    def create_and_run_tag_enforcement(self, enforcement_name, action_name, tag, close_result_modal=True):
        self.open_enforcement_panel()
        self.fill_enforcement_name(enforcement_name)
        self.open_action_tag_config()
        self.fill_enforcement_action_name(action_name)
        self.select_option(
            self.DROPDOWN_TAGS_CSS, self.DROPDOWN_TEXT_BOX_CSS, self.DROPDOWN_NEW_OPTION_CSS, tag
        )
        self.click_button(self.SAVE_AND_RUN_ENFORCEMENT_BUTTON)
        self.wait_for_element_present_by_text(self.ENFORCEMENT_TASK_SUCCESS_MESSAGE)
        if close_result_modal:
            self.click_button('Close')
            self.wait_for_modal_close()

    def enforce_action_on_query(self, query, action, filter_column_data: dict = None,
                                add_col_names: list = None, remove_col_names: list = None):
        self.run_filter_query(query)
        if filter_column_data:
            self.filter_column(filter_column_data.get('col_name'), filter_column_data.get('filter_list'))
        if add_col_names or remove_col_names:
            self.edit_columns(add_col_names=add_col_names, remove_col_names=remove_col_names)
        self.toggle_select_all_rows_checkbox()
        selected_count = len(self.find_rows_with_data())
        self.open_enforce_dialog()
        self.select_option_without_search(
            self.ENFORCEMENT_DIALOG_DROPDOWN_CSS,
            self.DROPDOWN_SELECTED_OPTION_CSS, action
        )
        self.click_button('Run')
        self.wait_for_element_present_by_text(self.ENFORCEMENT_TASK_SUCCESS_MESSAGE)
        self.click_button('Close')
        self.wait_for_modal_close()
        return selected_count

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
        self.select_query_logic_op(LOGIC_AND, parent=expressions[1])
        self.select_query_field(self.FIELD_LAST_SEEN, parent=expressions[1])
        self.select_query_comp_op(query_comp_day, parent=expressions[1])
        self.fill_query_value(5, parent=expressions[1])
        self.wait_for_table_to_load()
        self.close_dropdown()

    def add_query_last_seen_negative_value(self, adapter, field, com_op, value):
        self.click_query_wizard()
        self.select_column_adapter(adapter)
        self.select_query_field(field)
        self.select_query_comp_op(com_op)
        self.fill_query_value(value)
        self.wait_for_table_to_be_responsive()
        self.close_dropdown()

    def add_query_last_seen_last_day(self):
        self._add_query_last_seen(COMP_DAYS)

    def add_query_last_seen_next_day(self):
        self._add_query_last_seen(COMP_NEXT_DAYS)

    def run_enforcement_on_selected_device(self, enforcement_name, close_result_modal=True):
        self.open_enforce_dialog()
        self.select_option_without_search(dropdown_css_selector=self.ENFORCEMENT_DIALOG_DROPDOWN_CSS,
                                          selected_options_css_selector=self.DROPDOWN_SELECTED_OPTION_CSS,
                                          text=enforcement_name)
        self.click_button('Run')
        self.wait_for_element_present_by_text(self.ENFORCEMENT_TASK_SUCCESS_MESSAGE)
        # wait for the enforcement success modal animation to end.
        time.sleep(0.5)
        if close_result_modal:
            self.click_button('Close')
            self.wait_for_modal_close()

    def find_general_data_table_link(self, table_title):
        self.click_row()
        self.click_general_tab()
        self.click_tab(table_title)
        return self.driver.find_element_by_css_selector('.x-entity-general .x-tab.active .x-table .x-table-row td a')

    def find_general_data_basic_link(self, field_title):
        self.click_row()
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
        self.test_base.axonius_system.gui.login_user(DEFAULT_USER)
        self.assert_csv_field_match_ui_data(self.test_base.axonius_system.gui.get_entity_csv_field(
            'devices',
            self.driver.current_url.split('/')[-1],
            self.FIELD_NETWORK_INTERFACES_NAME,
            self.FIELD_MAC_NAME,
            search_text=search_text,
            timeout=CSV_TIMEOUT
        ))

    def check_search_text_result(self, text):
        self.wait_for_table_to_load()
        all_data = self.get_all_data()
        assert len(all_data)
        assert any(text in x for x in all_data)

    def check_search_text_result_in_column(self, text, column_name):
        self.wait_for_table_to_be_responsive()
        self.find_query_search_input().click()
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
        self.wait_for_table_to_be_responsive()

    def search(self, value):
        self.fill_filter(value)
        self.enter_search()
        self.wait_for_table_to_be_responsive()

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
        self.select_query_comp_op(COMP_DAYS, parent=expressions[0])
        self.fill_query_value(days, parent=expressions[0])
        self.wait_for_table_to_load()
        self.close_dropdown()

    def click_query_search_when_auto_query_disabled(self):
        self.click_button(text='Search',
                          button_class='ant-btn ant-btn-primary x-button')

    def check_csv_device_count(self):
        self.switch_to_page()
        self.refresh()
        self.run_filter_query(CSV_ADAPTER_FILTER)
        return self.count_entities()

    def check_aws_device_count(self):
        self.switch_to_page()
        self.refresh()
        self.run_filter_query(AWS_ADAPTER_FILTER)
        return self.count_entities()

    def get_device_count_by_connection_label(self, adapter: str = '', operator: str = '', value: str = '') -> int:
        self.switch_to_page()
        self.wait_for_table_to_be_responsive()
        self.click_query_wizard()
        self.set_connection_label_query(adapter, operator, value)
        self.close_dropdown()
        return self.count_entities()

    def set_connection_label_query(self, adapter: str = '', operator: str = '', value: str = ''):
        adapter_to_select = adapter if adapter else self.VALUE_ADAPTERS_GENERAL
        self.select_query_adapter(adapter_to_select)
        self.select_query_filter(attribute=self.FIELD_ADAPTER_CONNECTION_LABEL,
                                 operator=operator,
                                 value=value)
        self.wait_for_table_to_be_responsive()

    def check_connection_label_removed(self, label: str = ''):
        self.switch_to_page()
        self.wait_for_table_to_be_responsive()
        self.click_query_wizard()
        self.clear_query_wizard()
        expressions = self.find_expressions()
        self.select_query_field(self.FIELD_ADAPTER_CONNECTION_LABEL, parent=expressions[0])
        self.select_query_comp_op('equals', parent=expressions[0])
        with pytest.raises(NoSuchElementException):
            self.select_option(
                self.QUERY_VALUE_COMPONENT_CSS,
                self.DROPDOWN_TEXT_BOX_CSS,
                self.DROPDOWN_SELECTED_OPTION_CSS,
                label,
                expressions[0])
        # require in order to change focus to main page
        self.close_dropdown()
        self.clear_query_wizard()
        self.click_search()

    def build_connection_label_asset_entity_query(self, adapter_name, connection_label, operator, expression_index=0):
        expression = self.find_expressions()[expression_index]
        self.select_context_ent(expression)
        self.select_asset_entity_adapter(expression, adapter_name)
        children = self.get_asset_entity_children(expression)
        self.select_asset_entity_field(children[0], self.FIELD_ADAPTER_CONNECTION_LABEL)
        self.select_query_comp_op(operator, children[0])
        if operator == COMP_EQUALS:
            self.select_query_value_without_search(connection_label, parent=children[0])
        elif operator == COMP_IN:
            self.fill_query_string_value(connection_label, parent=children[0])

    def build_os_distribution_lt_gt_query(self, adapter_name, os_distribution, operator, expression_index=0):
        expression = self.find_expressions()[expression_index]
        self.select_query_adapter(adapter_name, parent=expression)
        self.select_query_field(self.FIELD_OS_DISTRIBUTION, parent=expression)
        self.select_query_comp_op(operator, parent=expression)
        self.select_query_value_without_search(os_distribution, parent=expression)
        self.wait_for_table_to_be_responsive()

    def get_host_name_aggregated_value(self):
        return [item.text for item in self.driver.find_elements_by_css_selector(self.HOST_NAME_AGGREGATED_FIELD_CSS)]

    def verify_saved_query_filter(self, query_name, query_filter):
        self.switch_to_page()
        self.execute_saved_query(query_name)
        assert self.get_query_search_input_value() == query_filter

    def add_saved_query_reference(self, query_name):
        self.add_query_expression()
        expressions = self.find_expressions()
        self.select_query_logic_op(LOGIC_AND, parent=expressions[1])
        self.select_query_field(self.FIELD_SAVED_QUERY, parent=expressions[0])
        self.select_query_value(query_name, parent=expressions[0])
        self.wait_for_table_to_load()
        self.close_dropdown()
