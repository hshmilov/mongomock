import os
import time
from enum import Enum
from typing import List, Tuple, Iterable
from collections import namedtuple

from testing.test_credentials.test_ad_credentials import WMI_QUERIES_DEVICE, ad_client1_details
from testing.test_credentials.test_shodan_credentials import CLIENT_DETAILS as shodan_client_details
from ui_tests.pages.entities_page import EntitiesPage

Task = namedtuple('Task', 'status stats name main_action trigger_query_name started_at completed_at')

ENFORCEMENT_WMI_EVERY_CYCLE = 'Run WMI on every cycle'
ENFORCEMENT_WMI_SAVED_QUERY = f'adapters_data.active_directory_adapter.hostname == "{WMI_QUERIES_DEVICE}"'
ENFORCEMENT_WMI_SAVED_QUERY_NAME = 'Execution devices'  # A strong device
ENFORCEMENT_WMI_REGISTER_KEY_XPATH = '//*[@class="md-input"]'

ACTION_WMI_REGISTRY_KEY__SELECTOR = '#reg_check_exists > div:nth-child({idx})'
ACTION_WMI_REGISTRY_KEY_OS_VERSION_SELECTOR = ACTION_WMI_REGISTRY_KEY__SELECTOR.format(idx='1')
ACTION_WMI_REGISTRY_KEY_CPU_TYPE_SELECTOR = ACTION_WMI_REGISTRY_KEY__SELECTOR.format(idx='2')
ACTION_WMI_REGISTRY_KEY_REMOVE_BUTTON = ACTION_WMI_REGISTRY_KEY__SELECTOR.format(idx='1') + ' > button'


class Period:
    EveryDiscovery = 'all_period'
    Daily = 'daily_period'
    Weekly = 'weekly_period'


class Trigger:
    NewEntities = 'New entities were added to results'
    PreviousEntities = 'Previous entities were subtracted from results'
    Above = 'The number of results is above...'
    Below = 'The number of results is below...'


class Action(Enum):
    send_emails = 'Send Email'
    send_csv_to_s3 = 'Send CSV to Amazon S3'
    create_notification = 'Push System Notification'
    carbonblack_isolate = 'Isolate in Carbon Black CB Response'
    cybereason_isolate = 'Isolate in Cybereason Deep Detect & Respond'
    cybereason_unisolate = 'Unisolate in Cybereason Deep Detect & Respond'
    notify_syslog = 'Send to Syslog System'
    tag = 'Add Tag'
    untag = 'Remove Tag'
    run_executable_windows = 'Deploy on Windows Device'
    run_wmi_scan = 'Run WMI Scan'
    run_windows_shell_command = 'Run Windows Shell Command'
    run_linux_ssh_scan = 'Run Linux SSH Scan'
    shodan_enrichment = 'Enrich Device Data with Shodan'
    censys_enrichment = 'Enrich Device Data with Censys'
    webscan_enrichment = 'Enrich Device Data with Web Server Information'
    scan_with_qualys = 'Add to Qualys Cloud Platform'
    change_ldap_attribute = 'Update LDAP Attributes of Users or Devices'
    ScanTenable = 'Add to Tenable'
    carbonblack_defense_change_policy = 'Change Carbon Black CB Defense Policy'
    carbonblack_defense_quarantine = 'Isolate Carbon Black CB Defense Device'
    carbonblack_defense_unquarantine = 'Unisolate Carbon Black CB Defense Device'
    tenable_sc_add_ips_to_asset = 'Add IPs to Tenable.sc Asset'
    tenable_io_add_ips_to_target_group = 'Add IPs to Tenable.io Target Group'
    create_jira_incident = 'Create Jira Issue'
    add_custom_data = 'Add Custom Data'


class ActionCategory:
    Deploy = 'Deploy Software'
    Run = 'Run Command'
    Notify = 'Notify'
    Isolate = 'Execute Endpoint Security Agent Action'
    Enrichment = 'Enrich Device or User Data'
    Utils = 'Axonius Utilities'
    Scan = 'Add Device to VA Scan'
    Patch = 'Patch Device'
    ManageAD = 'Manage Microsoft Active Directory (AD) Services'
    Incident = 'Create Incident'
    Block = 'Block Device in Firewall'


class EnforcementsPage(EntitiesPage):
    SAVE_AND_RUN_BUTTON_TEXT = 'Save & Run'
    TASK_IN_PROGRESS = 'Enforcement Task is in progress'
    NEW_ENFORCEMENT_BUTTON = '+ New Enforcement'
    ENFORCEMENT_NAME_ID = 'enforcement_name'
    TRIGGER_CONTAINER_CSS = '.x-trigger'
    TRIGGER_CONF_CONTAINER_CSS = '.x-trigger-config'
    MAIN_ACTION_TEXT = 'main action'
    SUCCESS_ACTIONS_TEXT = 'success actions'
    FAILURE_ACTIONS_TEXT = 'failure actions'
    POST_ACTIONS_TEXT = 'post actions'
    ACTION_LIBRARY_CONTAINER_CSS = '.x-action-library'
    ACTION_CONF_CONTAINER_CSS = '.x-action-config'
    ACTION_CONF_BODY_CSS = f'{ACTION_CONF_CONTAINER_CSS} .main'
    ACTION_RESULT_CONTAINER_CSS = '.x-action-result'
    ACTION_NAME_ID = 'action-name'
    API_KEY_ID = 'apikey'
    ACTION_BY_NAME_XPATH = '//div[@class=\'x-text-box\' and child::div[text()=\'{action_name}\']]'
    SELECT_VIEW_ENTITY_CSS = '.base-query .x-select-symbol .x-select-trigger'
    SELECT_VIEW_NAME_CSS = '.base-query .query-name .x-select-trigger'
    SELECT_SAVED_VIEW_TEXT_CSS = 'div.trigger-text'
    ENFORCEMENTS_CHECKBOX = '.x-checkbox .checkbox-container'
    TRIGGER_SECTION_CHECKBOX_XPATH = '//div[@class=\'header\' and child::*[@class=\'scheduling-title\' and ' \
                                     'text()=\'{section_name}\']]//div[@class=\'checkbox-container\']'
    ABOVE_INPUT_CSS = '.config .config-item .above'
    BELOW_INPUT_CSS = '.config .config-item .below'
    EDIT_ENFORCEMENT_XPATH = '//div[text()=\'{enforcement_name}\']'
    SEND_AN_EMAIL = 'Send an Email'
    DISABLED_ACTION_XPATH = (
        '//div[contains(@class, \'md-list-item-content\')]//div[@class=\'x-title disabled\' '
        'and .//text()=\'{action_name}\']'
    )
    CATEGORY_ACTIONS_XPATH = (
        '//div[contains(@class, \'md-list-item-container\') and child::div['
        './/text()=\'{category}\']]//div[@class=\'md-list-expand\']//div[@class=\'action-name\']'
    )
    CATEGORY_LIST_CSS = '.x-action-library > .md-list > .md-list-item > .md-list-item-container > .md-list-item-content'
    TASK_RESULT_CSS = '.x-action-result .x-summary div:nth-child({child_count})'
    TASK_RESULT_SUCCESS_CSS = TASK_RESULT_CSS.format(child_count=1)
    TASK_RESULT_FAILURE_CSS = TASK_RESULT_CSS.format(child_count=3)

    FIRST_ENFORCEMENT_EXECUTION_DIR_SEPERATOR = 'first-seperator'
    SECOND_ENFORCEMENT_EXECUTION_DIR_SEPERATOR = 'second-seperator'

    USE_ACTIVE_DIRECTORY_CREDENTIALS_CHECKBOX_LABEL = 'Use stored credentials from the Active Directory adapter'

    CLICKABLE_TABLE_ROW = '.x-table-row.clickable'
    CONFIRM_REMOVE_SINGLE = 'Remove Enforcement Set'
    CONFIRM_REMOVE_MULTI = 'Remove Enforcement Sets'
    ADDED_ACTION_XPATH = './/div[@class=\'content\' and .//text()=\'{action_name}\']'

    SPECIAL_TAG_ACTION = 'Special Tag Action'
    DEFAULT_TAG_NAME = 'Special'
    S3_BUCKET_ID = 's3_bucket'
    S3_ACCESS_KEY_ID = 'access_key_id'
    S3_SECRET_ACCESS_KEY_ID = 'secret_access_key'

    ACTION_WMI_REGISTRY_ADD_XPATH_ID = '.md-input'
    ACTION_WMI_REGISTRY_KEY_TEMPLATE = '//*[text()=\'{REG_KEY}\']'

    CUSTOM_DATA_XPATH = '//label[@for=\'{db_identifier}\'][contains(text(),\'{label}\')]/' \
                        'following-sibling::div[contains(text(),\'{value}\')]'

    COMPLETED_CELL_XPATH = '//tr/td[1]//div[text() = \'Completed\']'

    BREADCRUMB_TASK_NAME_XPATH = '//div[@class=\'header\']/*[@class=\'page-title\']/span[' \
                                 'preceding-sibling::div[@class=\'crumb\' and .//text()=\'enforcements\'] ' \
                                 'and preceding-sibling::div[@class=\'crumb\' and .//text()=\'tasks\']]'

    @property
    def url(self):
        return f'{self.base_url}/enforcements'

    @property
    def root_page_css(self):
        return 'li#enforcements.x-nav-item'

    def find_checkbox_with_label_before(self, text):
        return self.driver.find_element_by_xpath(self.CHECKBOX_WITH_SIBLING_LABEL_XPATH.format(label_text=text))

    def click_new_enforcement(self):
        self.wait_for_spinner_to_end()
        self.wait_for_table_to_load()
        self.wait_for_element_present_by_text(self.NEW_ENFORCEMENT_BUTTON)
        self.find_new_enforcement_button().click()
        self.wait_for_element_present_by_css(self.TRIGGER_CONTAINER_CSS)

    def find_new_enforcement_button(self):
        return self.get_button(self.NEW_ENFORCEMENT_BUTTON)

    def fill_enforcement_name(self, name):
        self.fill_text_field_by_element_id(self.ENFORCEMENT_NAME_ID, name)

    def wait_for_action_library(self):
        self.wait_for_element_present_by_css(self.ACTION_LIBRARY_CONTAINER_CSS)
        # Appearance animation time
        time.sleep(1)

    def wait_for_action_config(self):
        self.wait_for_element_present_by_css(self.ACTION_CONF_CONTAINER_CSS)
        # Appearance animation time
        time.sleep(0.6)

    def add_send_email(self):
        self.find_element_by_text(self.MAIN_ACTION_TEXT).click()
        self.wait_for_action_library()
        self.find_element_by_text(ActionCategory.Notify).click()
        # Opening animation time
        time.sleep(0.2)
        self.find_element_by_text(Action.send_emails.value).click()

    def add_main_action(self, category, action_type_name):
        self.find_element_by_text(self.MAIN_ACTION_TEXT).click()
        self.wait_for_action_library()
        self.find_element_by_text(category).click()
        # Opening animation time
        time.sleep(5)
        self.find_element_by_text(action_type_name).click()

    def add_main_action_shodan(self, action_name):
        self.add_main_action(ActionCategory.Enrichment, Action.shodan_enrichment.value)
        self.fill_action_name(action_name)
        self.fill_api_key(shodan_client_details['apikey'])
        self.save_action()
        self.click_save_button()
        # Due to a UI bug, the screen will change again to EC table
        time.sleep(10)

    def add_main_action_send_email(self, action_name, recipient):
        self.add_main_action(ActionCategory.Notify, Action.send_emails.value)
        self.fill_send_email_config(action_name, recipient=recipient)
        self.click_save_button()
        # Due to a UI bug, the screen will change again to EC table
        time.sleep(10)

    def add_send_csv_to_s3(self):
        self.find_element_by_text(self.MAIN_ACTION_TEXT).click()
        self.wait_for_action_library()
        self.find_element_by_text(ActionCategory.Notify).click()
        # Opening animation time
        time.sleep(0.2)
        self.find_element_by_text(Action.send_csv_to_s3.value).click()

    def tag_entities(self, name, tag, new_action=False, should_delete_unqueried=False):
        """
        Creates an "Add Tag" action to enforcement.
        :param name: Action name
        :param tag: Tag name
        :param new_action: Whether this is a new action.
        :param should_delete_unqueried: Whether the "Remove tag from entities not found in the Saved Query results"
        checkbox should be checked
        """
        # add new tag ( type name in the input and click on the create new option )
        self.wait_for_action_config()
        if new_action:
            self.fill_text_field_by_element_id(self.ACTION_NAME_ID, name)
        self.select_option(
            self.DROPDOWN_TAGS_CSS, self.DROPDOWN_TEXT_BOX_CSS, self.DROPDOWN_NEW_OPTION_CSS, tag
        )
        if should_delete_unqueried:
            self.click_toggle_button(
                self.find_checkbox_by_label('Remove tag from entities not found in the Saved Query results'),
                make_yes=should_delete_unqueried)
        self.click_button(self.SAVE_BUTTON)
        self.wait_for_element_present_by_text(name)

    def tag_entities_from_existing_values(self, name, tag, new_action=False, enter_key=False):
        # select tag from dropdown ( type name in the input and click on the filtered option )
        self.wait_for_action_config()
        if new_action:
            self.fill_text_field_by_element_id(self.ACTION_NAME_ID, name)
        if enter_key:
            self.enter_option(
                self.DROPDOWN_TAGS_CSS,
                self.DROPDOWN_TEXT_BOX_CSS,
                tag
            )
        else:
            self.select_option(
                self.DROPDOWN_TAGS_CSS,
                self.DROPDOWN_TEXT_BOX_CSS,
                self.DROPDOWN_SELECT_OPTION_CSS.format(title=tag),
                tag
            )
        self.click_button(self.SAVE_BUTTON)
        self.wait_for_element_present_by_text(name)

    def find_tags_dropdown(self, action_cond):
        self.find_element_by_text(action_cond).click()
        self.wait_for_action_library()
        self.find_element_by_text(ActionCategory.Utils).click()
        # Opening animation time
        time.sleep(0.2)

    def add_tag_entities(self, name=SPECIAL_TAG_ACTION, tag=DEFAULT_TAG_NAME, action_cond=MAIN_ACTION_TEXT,
                         should_delete_unqueried=False):
        self.find_tags_dropdown(action_cond)
        self.find_element_by_text(Action.tag.value).click()
        self.tag_entities(name, tag, new_action=True, should_delete_unqueried=should_delete_unqueried)

    def remove_tag_entities(self, name=SPECIAL_TAG_ACTION, tag=DEFAULT_TAG_NAME, action_cond=MAIN_ACTION_TEXT):
        self.find_tags_dropdown(action_cond)
        self.find_element_by_text(Action.untag.value).click()
        self.tag_entities_from_existing_values(name, tag, new_action=True)

    def select_tag_entities(self, name=SPECIAL_TAG_ACTION, tag=DEFAULT_TAG_NAME, action_cond=MAIN_ACTION_TEXT):
        self.find_tags_dropdown(action_cond)
        self.find_element_by_text(Action.tag.value).click()
        self.tag_entities_from_existing_values(name, tag, new_action=True, enter_key=True)

    def get_tag_dropdown_selected_value(self):
        return self.driver.find_element_by_css_selector(self.DROPDOWN_TAGS_VALUE_CSS).text

    def change_tag_entities(self, name=SPECIAL_TAG_ACTION, tag=DEFAULT_TAG_NAME, should_delete_unqueried=False):
        self.driver.find_element_by_xpath(self.ACTION_BY_NAME_XPATH.format(action_name=name)).click()
        self.tag_entities(name, tag, should_delete_unqueried=should_delete_unqueried)

    def fill_tag_all_text(self, tag_text):
        self.fill_text_field_by_element_id('tagAllName', tag_text)

    def fill_tag_new_text(self, tag_text):
        self.fill_text_field_by_element_id('tagNew', tag_text)

    def add_cb_isolate(self, name='Special Isolate Action', action_cond=MAIN_ACTION_TEXT):
        self.add_generic_action(ActionCategory.Isolate, Action.carbonblack_isolate.value, name, action_cond)

    def add_push_notification(self, name='Special Push Action', action_cond=MAIN_ACTION_TEXT):
        self.add_generic_action(ActionCategory.Notify, Action.create_notification.value, name, action_cond)

    def add_generic_action(self, action_category, action_type, name, action_cond=MAIN_ACTION_TEXT):
        self.find_element_by_text(action_cond).click()
        self.wait_for_action_library()
        self.find_element_by_text(action_category).click()
        # Opening animation time
        time.sleep(0.2)
        self.find_element_by_text(action_type).click()
        self.wait_for_action_config()
        self.fill_text_field_by_element_id(self.ACTION_NAME_ID, name)
        self.click_button(self.SAVE_BUTTON)
        self.wait_for_element_present_by_text(name)

    def get_action_categories(self):
        return [el.text.strip() for el in self.driver.find_elements_by_css_selector(self.CATEGORY_LIST_CSS)]

    def open_first_action_category(self):
        self.driver.find_element_by_css_selector(self.CATEGORY_LIST_CSS).click()
        # Opening animation time
        time.sleep(0.2)

    def open_action_category(self, category_name):
        self.find_element_by_text(category_name).click()
        # Opening animation time
        time.sleep(0.2)

    def get_action_category_items(self, category_name):
        self.open_action_category(category_name)
        return [
            el.text.strip()
            for el in self.find_elements_by_xpath(self.CATEGORY_ACTIONS_XPATH.format(category=category_name))
        ]

    def find_disabled_action(self, action_name):
        return self.driver.find_element_by_xpath(self.DISABLED_ACTION_XPATH.format(action_name=action_name))

    def click_action(self, action_name):
        self.find_element_by_text(action_name).click()

    def check_enforcement_checkbox(self, text):
        self.find_element_by_text(text).click()

    def check_config_section(self, section_name):
        self.driver.find_element_by_xpath(self.TRIGGER_SECTION_CHECKBOX_XPATH.format(section_name=section_name)).click()

    def check_scheduling(self):
        self.check_config_section('Add Scheduling')

    def check_conditions(self):
        self.check_config_section('Add Conditions')

    def check_condition_added(self):
        self.check_enforcement_checkbox(Trigger.NewEntities)

    def check_condition_subracted(self):
        self.check_enforcement_checkbox(Trigger.PreviousEntities)

    def check_above(self):
        self.check_enforcement_checkbox(Trigger.Above)

    def check_below(self):
        self.check_enforcement_checkbox(Trigger.Below)

    def check_new_entities(self):
        self.check_enforcement_checkbox('Run on added entities only')

    def add_push_system_notification(self, name='Special Push Notification'):
        self.find_element_by_text(self.MAIN_ACTION_TEXT).click()
        self.wait_for_action_library()
        self.find_element_by_text(ActionCategory.Notify).click()
        # Opening animation time
        time.sleep(0.2)
        self.find_element_by_text(Action.create_notification.value).click()
        self.wait_for_action_config()
        self.fill_action_name(name)
        self.click_button(self.SAVE_BUTTON)
        self.wait_for_element_present_by_text(name)

    def add_run_wmi_scan(self, *regkey, name='Run WMI Scan'):

        def add_register_key(*args):
            register_keys = self.driver.find_element_by_xpath(ENFORCEMENT_WMI_REGISTER_KEY_XPATH)
            assert register_keys.get_attribute('placeholder') == 'Add...'
            for regkey in args:
                register_keys.send_keys(regkey + ',')
                time.sleep(0.6)

        self.find_element_by_text(self.MAIN_ACTION_TEXT).click()
        self.wait_for_action_library()
        self.find_element_by_text(ActionCategory.Run).click()
        # Opening animation time
        time.sleep(0.6)
        self.find_element_by_text(Action.run_wmi_scan.value).click()
        self.wait_for_action_config()
        self.find_checkbox_with_label_before(self.USE_ACTIVE_DIRECTORY_CREDENTIALS_CHECKBOX_LABEL).click()
        self.fill_action_name(name)
        if regkey:
            add_register_key(*regkey)
        self.click_button(self.SAVE_BUTTON)
        self.wait_for_element_present_by_text(name)

    def add_custom_data(self, action_name, field_name, field_value):
        self.find_element_by_text(self.MAIN_ACTION_TEXT).click()
        self.wait_for_action_library()
        self.find_element_by_text(ActionCategory.Utils).click()
        # wait for animation ends
        time.sleep(0.2)
        self.find_element_by_text(Action.add_custom_data.value).click()
        self.wait_for_action_config()

        # fill configuration form data
        self.fill_action_name(action_name)
        self.fill_text_field_by_css_selector(css_selector='input#field_name', value=field_name)
        self.fill_text_field_by_css_selector(css_selector='input#field_value', value=field_value)
        self.click_button(self.SAVE_BUTTON)

        # the action name appears in the Main Action slot
        self.wait_for_element_present_by_text(action_name)

    def create_new_enforcement_with_custom_data(self, enforcement_name, action_name, field_name, field_value):
        self.switch_to_page()

        # field name is similar to how generic 'Host Name' saved on db
        self.click_new_enforcement()
        self.fill_enforcement_name(enforcement_name)
        self.add_custom_data(action_name, field_name, field_value)
        self.click_save_button()

    def fill_action_name(self, name):
        self.fill_text_field_by_element_id(self.ACTION_NAME_ID, name)

    def fill_api_key(self, api_key):
        self.fill_text_field_by_element_id(self.API_KEY_ID, api_key)

    def add_notify_syslog(self, name='Special Syslog Notification', action_cond=MAIN_ACTION_TEXT, severity='warning'):
        # 'warning' by default, because our syslog doesn't like logs sent using "INFO"
        # It is an issue with our syslog's configuration, and it's not worth the time fixing
        self.find_element_by_text(action_cond).click()
        self.wait_for_action_library()
        self.find_element_by_text(ActionCategory.Notify).click()
        # Opening animation time
        time.sleep(0.2)
        self.find_element_by_text(Action.notify_syslog.value).click()
        self.wait_for_action_config()
        self.fill_text_field_by_element_id(self.ACTION_NAME_ID, name)
        self.select_option_without_search(
            f'{self.ACTION_CONF_CONTAINER_CSS} .x-dropdown.x-select', self.DROPDOWN_SELECTED_OPTION_CSS, severity
        )
        self.click_button(self.SAVE_BUTTON)
        self.wait_for_element_present_by_text(name)

    def add_deploy_software(self, name='Deploy Special Software'):
        self.find_element_by_text(self.MAIN_ACTION_TEXT).click()
        self.wait_for_action_library()
        self.find_element_by_text(ActionCategory.Deploy).click()
        # Opening animation time
        time.sleep(0.2)
        self.find_element_by_text(Action.run_executable_windows.value).click()
        self.wait_for_action_config()
        self.fill_text_field_by_element_id(self.ACTION_NAME_ID, name)
        self.find_checkbox_with_label_before(self.USE_ACTIVE_DIRECTORY_CREDENTIALS_CHECKBOX_LABEL).click()
        exe_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                '../../../shared_readonly_files/test_binary.exe'))
        self.upload_file_by_id('executable', open(exe_path, 'rb').read(), is_bytes=True)
        time.sleep(2)
        self.click_button(self.SAVE_BUTTON)
        self.wait_for_element_present_by_text(name)

    def add_run_windows_command(self, name, files: List[Tuple[str, bytes]] = None):
        self.find_element_by_text(self.MAIN_ACTION_TEXT).click()
        self.wait_for_action_library()
        self.find_element_by_text(ActionCategory.Run).click()
        # Opening animation time
        time.sleep(0.2)
        self.find_element_by_text(Action.run_windows_shell_command.value).click()
        self.wait_for_element_present_by_css(self.ACTION_CONF_CONTAINER_CSS)
        # Appearance animation time
        time.sleep(0.6)
        self.fill_text_field_by_element_id(self.ACTION_NAME_ID, name)
        self.find_checkbox_with_label_before(self.USE_ACTIVE_DIRECTORY_CREDENTIALS_CHECKBOX_LABEL).click()
        param_line = f'dir && echo {self.FIRST_ENFORCEMENT_EXECUTION_DIR_SEPERATOR}'
        files = files or []
        for file_num, file_data in enumerate(files):
            file_prefix, file_contents = file_data
            self.click_button('+', button_class='x-button light',
                              scroll_into_view_container=self.ACTION_CONF_BODY_CSS)
            file_name = self.upload_file_by_id(
                str(file_num),
                file_contents,
                is_bytes=isinstance(file_contents, bytes),
                prefix=file_prefix
            )
            if param_line:
                param_line += ' && '
            param_line += f'type {file_name} && del {file_name}'
        if param_line:
            param_line += ' && '
        param_line += f'echo done && echo {self.SECOND_ENFORCEMENT_EXECUTION_DIR_SEPERATOR} && dir'
        self.fill_text_field_by_element_id('params', param_line)
        self.click_button(self.SAVE_BUTTON)
        self.wait_for_element_present_by_text(name)

    def add_ldap_attribute(self, name='Update LDAP Attribute'):
        self.find_element_by_text(self.MAIN_ACTION_TEXT).click()
        self.wait_for_action_library()
        self.find_element_by_text(ActionCategory.ManageAD).click()
        # Opening animation time
        time.sleep(0.2)
        self.find_element_by_text(Action.change_ldap_attribute.value).click()
        self.wait_for_action_config()
        self.fill_text_field_by_element_id(self.ACTION_NAME_ID, name)
        self.fill_text_field_by_element_id('username', ad_client1_details['user'])
        self.fill_text_field_by_element_id('password', ad_client1_details['password'])
        self.click_button('+', button_class='x-button light',
                          scroll_into_view_container=self.ACTION_CONF_BODY_CSS)
        self.fill_text_field_by_element_id('attribute_name', 'info')
        self.fill_text_field_by_element_id('attribute_value', 'test123')
        time.sleep(2)
        self.click_button(self.SAVE_BUTTON)
        self.wait_for_element_present_by_text(name)

    def select_trigger(self):
        self.driver.find_element_by_css_selector(self.TRIGGER_CONTAINER_CSS).click()
        self.wait_for_element_present_by_css(self.TRIGGER_CONF_CONTAINER_CSS)
        # Appearance animation time
        time.sleep(0.6)

    def save_trigger(self):
        self.click_button(
            self.SAVE_BUTTON,
            scroll_into_view_container=self.TRIGGER_CONF_CONTAINER_CSS,
            context=self.driver.find_element_by_css_selector(self.TRIGGER_CONF_CONTAINER_CSS),
        )

    def select_saved_view(self, text, entity='Devices'):
        self.select_option_without_search(self.SELECT_VIEW_ENTITY_CSS, self.DROPDOWN_SELECTED_OPTION_CSS, entity)
        self.select_option(self.SELECT_VIEW_NAME_CSS,
                           self.DROPDOWN_TEXT_BOX_CSS,
                           self.DROPDOWN_SELECTED_OPTION_CSS,
                           text,
                           partial_text=False)

    def save_action(self):
        self.click_button(
            self.SAVE_BUTTON,
            scroll_into_view_container=self.ACTION_CONF_CONTAINER_CSS,
            context=self.driver.find_element_by_css_selector(self.ACTION_CONF_CONTAINER_CSS),
        )

    def click_save_button(self):
        self.click_button('Save & Exit')

    def click_run_button(self):
        self.click_button(self.SAVE_AND_RUN_BUTTON_TEXT, partial_class=True)

    def wait_for_task_in_progress_toaster(self):
        self.wait_for_toaster_to_end(self.TASK_IN_PROGRESS)

    def click_tasks_button(self):
        self.click_button('View Tasks', partial_class=True)

    def select_all_enforcements(self):
        self.driver.find_element_by_css_selector(self.ENFORCEMENTS_CHECKBOX).click()

    def remove_selected_enforcements(self, confirm=False):
        if confirm:
            self.remove_selected_with_safeguard(self.CONFIRM_REMOVE_SINGLE, self.CONFIRM_REMOVE_MULTI)
        else:
            self.remove_selected_with_safeguard()

    def choose_period(self, period):
        self.wait_for_element_present_by_id(period).click()

    def get_all_periods_sorted(self):
        return [x.text for x in self.driver.find_elements_by_css_selector('div.list-item > label.radio-label')]

    def fill_above_value(self, value):
        self.fill_text_field_by_css_selector(self.ABOVE_INPUT_CSS, value)

    def get_above_value(self):
        return self.driver.find_element_by_css_selector(self.ABOVE_INPUT_CSS).get_attribute('value')

    def fill_below_value(self, value):
        self.fill_text_field_by_css_selector(self.BELOW_INPUT_CSS, value)

    def edit_enforcement(self, enforcement_name):
        self.driver.find_element_by_xpath(self.EDIT_ENFORCEMENT_XPATH.format(enforcement_name=enforcement_name)).click()

    def get_saved_query_text(self):
        return self.driver.find_element_by_css_selector(self.SELECT_SAVED_VIEW_TEXT_CSS).get_attribute('title')

    def assert_screen_is_restricted(self):
        self.switch_to_page_allowing_failure()
        self.find_element_by_text('You do not have permission to access the Enforcements screen')
        self.click_ok_button()

    def create_basic_empty_enforcement(self, enforcement_name):
        self.switch_to_page()
        # for some reason, this switch_to_page doesn't work from here sometimes
        time.sleep(1)
        self.switch_to_page()
        self.click_new_enforcement()
        self.fill_enforcement_name(enforcement_name)

    def create_basic_enforcement(self,
                                 enforcement_name,
                                 enforcement_view=None,
                                 trigger=True,
                                 schedule=True,
                                 enforce_added=False,
                                 save=True):
        self.create_basic_empty_enforcement(enforcement_name)
        if trigger:
            self.select_trigger()
            if enforce_added:
                self.check_new_entities()
            if schedule:
                self.check_scheduling()
            self.select_saved_view(enforcement_view)
            if save:
                self.save_trigger()

    def create_notifying_enforcement(self,
                                     enforcement_name,
                                     enforcement_view,
                                     added=True,
                                     subtracted=True,
                                     above=0,
                                     below=0):

        self.create_basic_enforcement(enforcement_name, enforcement_view, save=False)
        self.check_conditions()
        if added:
            self.check_condition_added()
        if subtracted:
            self.check_condition_subracted()
        if above:
            self.check_above()
            self.fill_above_value(above)
        if below:
            self.check_below()
            self.fill_below_value(below)
        self.save_trigger()

        self.add_push_system_notification(enforcement_name)
        self.click_save_button()
        self.wait_for_spinner_to_end()
        self.wait_for_table_to_load()

    def create_notifying_enforcement_above(self, alert_name, alert_query, above):
        self.create_notifying_enforcement(alert_name,
                                          alert_query,
                                          added=False,
                                          subtracted=False,
                                          above=above,
                                          below=0)

    def create_notifying_enforcement_below(self, alert_name, alert_query, below):
        self.create_notifying_enforcement(alert_name,
                                          alert_query,
                                          added=False,
                                          subtracted=False,
                                          above=0,
                                          below=below)

    def create_deploying_enforcement(self, enforcement_name, enforcement_view):
        self.create_basic_enforcement(enforcement_name, enforcement_view)
        self.add_deploy_software(enforcement_name)
        self.click_save_button()
        self.wait_for_table_to_load()

    def create_run_wmi_enforcement(self, *regkeys):
        self.switch_to_page()
        self.create_basic_enforcement(ENFORCEMENT_WMI_EVERY_CYCLE, ENFORCEMENT_WMI_SAVED_QUERY_NAME)
        self.add_run_wmi_scan(*regkeys, name=ENFORCEMENT_WMI_EVERY_CYCLE)
        self.add_tag_entities(name='Great Success', tag='Great Success', action_cond=self.SUCCESS_ACTIONS_TEXT)
        self.click_save_button()
        self.wait_for_table_to_load()

    def create_run_wmi_scan_on_each_cycle_enforcement(self):
        # First, check if we have it.
        self.switch_to_page()
        try:
            self.find_element_by_text(ENFORCEMENT_WMI_EVERY_CYCLE)
            # no need to re-create it.
            return
        except Exception:
            pass
        self.test_base.devices_page.switch_to_page()
        self.test_base.devices_page.run_filter_and_save(ENFORCEMENT_WMI_SAVED_QUERY_NAME, ENFORCEMENT_WMI_SAVED_QUERY)
        self.create_run_wmi_enforcement()

    def add_deploying_consequences(self, enforcement_name, success_tag_name, failure_tag_name, failure_isolate_name):
        self.switch_to_page()
        self.refresh()
        self.wait_for_table_to_load()
        self.edit_enforcement(enforcement_name)
        self.wait_for_action_config()
        self.add_tag_entities(name=success_tag_name, tag='Specially Deployed', action_cond=self.SUCCESS_ACTIONS_TEXT)
        self.add_cb_isolate(name=failure_isolate_name, action_cond=self.FAILURE_ACTIONS_TEXT)
        self.wait_for_action_config()
        self.add_tag_entities(
            name=failure_tag_name, tag='Missing Special Deploy', action_cond=self.FAILURE_ACTIONS_TEXT
        )
        self.click_save_button()
        self.wait_for_table_to_load()

    def create_tag_enforcement(self,
                               enforcement_name,
                               enforcement_view,
                               name=SPECIAL_TAG_ACTION,
                               tag=DEFAULT_TAG_NAME,
                               action_cond=MAIN_ACTION_TEXT):
        self.create_basic_enforcement(enforcement_name, enforcement_view, save=False)
        self.select_trigger()
        self.check_scheduling()
        self.select_saved_view(enforcement_view)
        self.save_trigger()
        self.add_tag_entities(name, tag, action_cond)
        self.click_save_button()
        self.wait_for_spinner_to_end()
        self.wait_for_table_to_load()

    def is_severity_selected(self, severity):
        return self.driver.find_element_by_css_selector(severity).is_selected()

    def is_period_selected(self, period):
        return self.driver.find_element_by_id(period).is_selected()

    def is_action_selected(self, action):
        return self.find_element_by_text(action) is not None

    def is_trigger_selected(self, trigger):
        element = self.find_checkbox_container_by_label(trigger)
        return element.get_attribute('class') == 'x-checkbox grid-span2 checked'

    def find_checkbox_container_by_label(self, label_text):
        return self.driver.find_element_by_xpath(self.DIV_BY_LABEL_TEMPLATE.format(label_text=label_text))

    def wait_for_action_result(self):
        self.wait_for_element_present_by_css(self.ACTION_RESULT_CONTAINER_CSS)
        # Appearance animation time
        time.sleep(3)

    def select_task_action(self, name):
        self.find_element_by_text(name).click()
        self.wait_for_action_result()

    def find_task_action_success(self, name):
        self.select_task_action(name)
        assert self.find_element_by_text('Entities Succeeded')
        return self.driver.find_element_by_css_selector(self.TASK_RESULT_SUCCESS_CSS)

    def find_task_action_failure(self, name):
        self.select_task_action(name)
        assert self.find_element_by_text('Entities Failed')
        return self.driver.find_element_by_css_selector(self.TASK_RESULT_FAILURE_CSS)

    def fill_action_library_search(self, text):
        self.fill_text_field_by_css_selector('.x-action-library .x-search-input .input-value', text)

    def find_action_library_tip(self, tip_text):
        library_tip = self.wait_for_element_present_by_css('.x-action-library-tip')
        return self.find_element_by_text(tip_text, element=library_tip)

    def fill_send_email_config(self, name, recipient=None, body=None, attach_csv=False):
        self.wait_for_action_config()
        self.fill_text_field_by_element_id(self.ACTION_NAME_ID, name)
        if recipient:
            self.fill_text_field_by_css_selector('.md-input', recipient, context=self.find_field_by_label('Recipients'))
            elem = self.find_field_by_label('Recipients').find_element_by_css_selector('.md-input')
            self.key_down_enter(elem)
        if body:
            custom_message_element = self.driver.find_element_by_xpath(
                self.DIV_BY_LABEL_TEMPLATE.format(label_text='Custom message (up to 200 characters)')
            )
            self.fill_text_field_by_tag_name('textarea', body, context=custom_message_element)
            assert custom_message_element.find_element_by_tag_name('textarea').get_attribute('value') == body[:200]
        if attach_csv:
            attach_csv_checkbox = self.driver.find_element_by_xpath(
                self.DIV_BY_LABEL_TEMPLATE.format(label_text='Attach CSV with query results'))
            attach_csv_checkbox.find_element_by_class_name('x-checkbox').click()
        self.click_button(self.SAVE_BUTTON)
        self.wait_for_element_present_by_text(name)

    def fill_send_csv_to_s3_config(self, name, s3_bucket,
                                   access_key=None,
                                   secret_access_key=None,
                                   attach_iam_role=False):
        self.wait_for_action_config()
        self.fill_text_field_by_element_id(self.ACTION_NAME_ID, name)
        self.fill_text_field_by_element_id(self.S3_BUCKET_ID, s3_bucket)
        if access_key:
            self.fill_text_field_by_element_id(self.S3_ACCESS_KEY_ID, access_key)
        if secret_access_key:
            self.fill_text_field_by_element_id(self.S3_SECRET_ACCESS_KEY_ID, secret_access_key)
        if attach_iam_role:
            attach_iam_rols_checkbox = self.driver.find_element_by_xpath(
                self.DIV_BY_LABEL_TEMPLATE.format(label_text='Use attached IAM role'))
            attach_iam_rols_checkbox.find_element_by_class_name('x-checkbox').click()
        self.click_button(self.SAVE_BUTTON)
        self.wait_for_element_present_by_text(name)

    def find_disabled_save_action(self):
        return self.driver.find_element_by_css_selector(self.ACTION_CONF_CONTAINER_CSS).find_element_by_xpath(
            self.DISABLED_BUTTON_XPATH.format(button_text=self.SAVE_BUTTON))

    def find_existing_trigger(self):
        return self.wait_for_element_present_by_text('Trigger')

    def navigate_task_success_results(self, action_name):
        self.click_row()
        self.wait_for_element_present_by_text(action_name)
        self.wait_for_action_result()
        self.find_task_action_success(action_name).click()

    def get_task_status(self, row_index=1):
        return self.get_row_cell_text(row_index=row_index, cell_index=1)

    def get_tasks_data_from_table(self) -> Iterable[Task]:

        table = self.driver.find_element_by_css_selector(self.TABLE_CLASS)

        # Start from index 1 to avoid the table head
        rows = table.find_elements_by_css_selector(self.CLICKABLE_TABLE_ROW)[1:]
        for row in rows:
            # Get all columns [status, stats, name, main_action, trigger_query_name, started_at, completed_at]
            status = row.find_elements_by_tag_name('td')[0].text
            stats = row.find_elements_by_tag_name('td')[1].text
            name = row.find_elements_by_tag_name('td')[2].text
            main_action = row.find_elements_by_tag_name('td')[3].text
            trigger_query_name = row.find_elements_by_tag_name('td')[4].text
            started_at = row.find_elements_by_tag_name('td')[5].text
            completed_at = row.find_elements_by_tag_name('td')[6].text

            yield Task(status=status, stats=stats, name=name,
                       main_action=main_action, trigger_query_name=trigger_query_name,
                       started_at=started_at, completed_at=completed_at)

    def click_remove_first_reg_key_in_wmi_action(self):
        # delete reg key # 1
        self.driver.find_element_by_css_selector(ACTION_WMI_REGISTRY_KEY_REMOVE_BUTTON).click()
        time.sleep(0.6)  # flaky with 0.2

    def get_wmi_action_registry_keys_input_text(self):
        return self.driver.find_element_by_id('reg_check_exists').text

    def get_wmi_action_register_key_text(self, key_index=0):
        key = self.driver.find_element_by_css_selector(ACTION_WMI_REGISTRY_KEY__SELECTOR.format(idx=key_index))
        time.sleep(0.6)  # flaky with 0.2
        return key.text

    def verify_wmi_action_register_keys(self, *regkeys, delete_after_verification=False):
        # verify reg key
        self.find_element_by_text(ENFORCEMENT_WMI_EVERY_CYCLE).click()
        time.sleep(0.2)
        idx = 0
        if regkeys:
            for reg_key in regkeys:
                idx += 1
                assert self.get_wmi_action_register_key_text(idx) == reg_key
                time.sleep(0.2)
        if delete_after_verification:
            for _ in regkeys:
                self.click_remove_first_reg_key_in_wmi_action()

        assert self.get_wmi_action_registry_keys_input_text() == ''

    def get_task_name(self):
        return self.find_element_by_xpath(self.BREADCRUMB_TASK_NAME_XPATH).text
