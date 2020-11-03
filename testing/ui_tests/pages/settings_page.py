import time
import collections
from uuid import uuid4
from datetime import datetime, timedelta
import dateutil

from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, \
    ElementNotInteractableException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from axonius.adapter_base import WEEKDAYS
from axonius.consts.gui_consts import PROXY_ERROR_MESSAGE, ENABLE_PBKDF2_FED_BUILD_ONLY_ERROR
from axonius.consts.plugin_consts import CORRELATION_SCHEDULE_HOURS_INTERVAL, AWS_SM_ACCESS_KEY_ID, \
    AWS_SM_SECRET_ACCESS_KEY, AWS_SM_REGION
from axonius.consts.gui_consts import FeatureFlagsNames
from services.axon_service import TimeoutException
from test_credentials.test_gui_credentials import DEFAULT_USER
from test_helpers.utils import get_datetime_format_by_gui_date
from ui_tests.pages.page import PAGE_BODY, TAB_BODY, Page

# pylint: disable=too-many-lines,no-member


class SettingsPage(Page):
    SCHEDULE_RATE_CSS = '#system_research_rate'
    DEFAULT_SCHEDULE_RATE = '12'
    DEFAULT_SCHEDILE_DATE = '13:00'
    GLOBAL_SETTINGS_CSS = 'li#global-settings-tab'
    CERTIFICATE_SETTINGS_CSS = 'li#certificate-settings-tab'
    GUI_SETTINGS_CSS = 'li#gui-settings-tab'
    IDENTITY_PROVIDERS_SETTINGS_CSS = 'li#identity-providers-settings-tab'
    TUNNEL_SETTINGS_CSS = 'li#tunnel-settings-tab'
    LIFECYCLE_SETTINGS_CSS = 'li#research-settings-tab'
    MANAGE_USERS_CSS = 'li#manage-users-tab'
    MANAGE_ROLES_CSS = 'li#manage-roles-tab'
    FEATURE_FLAGS_CSS = 'li#feature-flags-tab'
    ABOUT_CSS = 'li#about-tab'
    SEND_EMAILS_LABEL = 'Send emails'
    EVALUATE_ROLE_ASSIGNMENT_ON_DDL = 'label[for=evaluate_role_assignment_on] + div.x-select'
    DISABLE_REMEMBER_ME = 'Disable \'Remember me\''
    SESSION_TIMEOUT_LABEL = 'Enable session timeout'
    QUERIES_CACHE_LABEL = 'Enable caching on recently used queries'
    GETTING_STARTED_LABEL = 'Enable Getting Started with Axonius checklist'
    GLOBAL_SSL_LABEL = 'Configure custom SSL certificate'
    REMOTE_SUPPORT_LABEL_OLD = 'Remote Support - Warning: turning off this feature prevents Axonius from' \
                               '                             updating the system and can lead' \
                               ' to slower issue resolution time.                             ' \
                               'Note: anonymized analytics must be enabled for remote support'
    REMOTE_SUPPORT_LABEL = 'Remote Access'
    ANALYTICS_LABEL_OLD = 'Anonymized Analytics - Warning: turning off this feature prevents Axonius from' \
                          '                             proactively detecting issues and notifying about errors.'
    ANALYTICS_LABEL = 'Anonymized Analytics'
    PROVISION_LABEL = 'Remote Support'
    USE_SYSLOG_LABEL = 'Use Syslog'
    ENFORCE_PASSWORD_POLICY = 'Enforce password complexity'
    PASSWORD_EXPIRATION_LABEL = 'Enable password expiration'
    PASSWORD_EXPIRATION_FIELD_ID = 'password_expiration_days'
    LDAP_LOGINS_LABEL = 'Allow LDAP logins'
    OKTA_LOGINS_LABEL = 'Allow Okta logins'
    EXACT_SEARCH_LABEL = 'Use exact match for assets search'
    ACTIVATE_BANDICOOT_LABEL = 'Run Bandicoot container (results will be available next cycle)'
    EXPERIMENTAL_API_LABEL = ''
    NOTIFY_ON_ADAPTERS_FETCH_LABEL = 'Notify on adapters fetch'
    SAML_LOGINS_LABEL = 'Allow SAML-based logins'
    SAML_AUTO_REDIRECT_LABEL = 'Automatically redirect all logins to the identity provider'
    TRIAL_MODE_FLAG_LABEL = 'Is trial mode'
    GLOBAL_SETTINGS_ADVANCED_SETTINGS_LABEL = 'Advanced Settings'
    EMAIL_PORT_ID = 'smtpPort'
    EMAIL_HOST_ID = 'smtpHost'
    ERROR_TEXT_CSS = '.error-text'
    SYSLOG_HOST = 'syslogHost'
    SYSLOG_PORT = 'syslogPort'
    TIMEOUT_ID = 'timeout'
    SYSLOG_SSL_CSS_DROPBOX = '[for=use_ssl]+div'
    SYSLOG_SSL_CSS_DROPBOX_OPTIONS = '[for=use_ssl]+.x-dropdown>.content .x-select-options>.x-select-option'
    FRESH_SERVICE_DOMAIN = 'domain'
    FRESH_SERVICE_API_KEY = 'api_key'
    FRESH_SERVICE_ADMIN_EMAIL = 'admin_email'
    SAML_IDP = 'idp_name'
    SAML_METADATA = 'metadata_url'
    SAML_AXONIUS_EXTERNAL_URL = 'axonius_external_url'
    HISTORY_GATHERED = 'Enable scheduled historical snapshot'
    DC_ADDRESS = 'dc_address'
    GROUP_CN = 'group_cn'
    ALLOW_GOOGLE_LOGINS = 'Allow Google logins'
    GOOGLE_CLIENT_ID_OLD = 'client_id'
    GOOGLE_CLIENT_ID = 'client'
    GOOGLE_EMAIL_OF_ADMIN = 'account_to_impersonate'
    READ_ONLY_PERMISSION = 'Read only'
    READ_WRITE_PERMISSION = 'Read and edit'
    RESTRICTED_PERMISSION = 'Restricted'
    SAVED_SUCCESSFULLY_TOASTER = 'Saved Successfully'
    ROLE_SUCCESSFULLY_CREATED_TOASTER = 'Role created'
    ROLE_SUCCESSFULLY_SAVED_TOASTER = 'Role saved'
    DELETED_ROLE_SUCCESSFULLY_TOASTER = 'Role deleted'
    SAVED_SUCCESSFULLY_PERMISSIONS_TOASTER = 'User permissions saved'
    BAD_PROXY_TOASTER = PROXY_ERROR_MESSAGE
    SELECT_ROLE_DIV_CSS = 'div.item.form__role'
    SELECT_ROLE_CSS = 'div.item.form__role .ant-select'
    SELECT_ROLE_LIST_BOX_CSS = '.ant-select-dropdown-menu'
    SELECT_USER_ROLE_CSS = '.user-permissions .user-role .x-select'
    SELECT_OPTION_CSS = 'div.x-select-option'
    ADMIN_ROLE = 'Admin'
    READ_ONLY_ROLE = 'Read Only User'
    VIEWER_ROLE = 'Viewer'
    RESTRICTED_ROLE = 'Restricted'
    USE_PROXY = 'Proxy enabled'
    USE_PASSWORD_MGR_VAULT = 'Use Password Manager'
    USE_AMAZON = 'Enable Amazon S3 integration'
    USE_GUI_SSL = 'Configure custom SSL certificate'
    USE_CORRELATION_SCHEDULE = 'Enable correlation schedule'
    USE_CYBERARK_VAULT = 'Use CyberArk'
    CORRELATION_HOUR_ERROR = '\'Number of hours between correlations\' has an illegal value'
    AMAZON_BUCKET_NAME_FIELD = 'bucket_name'
    VALUES_COUNT_PER_COLUMN_DROPDOWN_CSS = 'label[for="defaultColumnLimit"]~.x-dropdown.x-select'
    VALUES_COUNT_ENTITIES_PER_PAGE_CSS = 'label[for="defaultNumOfEntitiesPerPage"]~.x-dropdown.x-select'
    DATE_FORMAT_CSS = 'label[for="datetime_format"]~.x-dropdown.x-select'
    SAFEGUARD_REMOVE_BUTTON_TEXT = 'Delete Role'
    XPATH_BY_CLASS_NAME = '//*[contains(@class, \'{name}\')]'
    DATEPICKER_CLASS_NAME = 'x-date-edit'
    TRIAL_DATE_PICKER_CSS = f'div.item_trial_end .{DATEPICKER_CLASS_NAME}'
    CONTRACT_DATE_PICKER_CSS = f'.item_expiry_date .{DATEPICKER_CLASS_NAME}'
    # sorry - but it's not my fault
    # https://axonius.atlassian.net/browse/AX-2991
    # those are the fully fledged css selectors for the elements
    CERT_ELEMENT_SELECTOR = 'div.x-tab.active.certificate-settings-tab input[id=cert_file]'
    PRIVATE_ELEMENT_SELECTOR = 'div.x-tab.active.certificate-settings-tab input[id=private_key]'
    MUTUAL_TLS_CERTIFICATE_SELECTOR = 'div.x-tab.active.certificate-settings-tab input[id=ca_certificate]'
    CERT_ELEMENT_FILENAME_SELECTOR = 'div.x-tab.active.certificate-settings-tab input[id=cert_file] + '\
                                     'div[class=file] div[class=file__name]'
    PRIVATE_ELEMENT_FILENAME_SELECTOR = 'div.x-tab.active.certificate-settings-tab input[id=private_key] ' \
                                        '+ div[class=file] div[class=file__name]'
    CSV_IP_TO_LOCATION_SELECTOR = 'div.x-tab.active.global-settings-tab ' \
                                  'input[id=csv_ip_location_file]'

    TABS_BODY_CSS = '.x-tabs .body'

    SAVE_USER_BUTTON = 'Save'
    UPDATE_USER_BUTTON = 'Update User'
    USER_DETAILS_SELECTOR = '.user-details-title'

    ROLE_PLACEHOLDER_CSS = '.user-role .x-select .placeholder'

    PERMISSION_LABEL_DEVICES = 'Devices'
    PERMISSION_LABEL_DASHBOARD = 'Dashboard'
    PERMISSION_LABEL_USERS = 'Users'

    CA_CERTIFICATE_ENABLED = '//*[contains(text(),\'CA certificate\')]'

    CA_ADD_CERT_BUTTON = '#ca_files ~ .x-button.ant-btn-light'
    CA_ADD_CERT_BUTTON_CSS = 'div.x-array-edit > div:nth-child(2) > div > div > div:nth-child(3) > div > div > button'

    CA_CERTS_FILES = '#ca_files + div > div:nth-child({file_index})'

    CA_CERT_DELETE_BUTTON = f'{CA_CERTS_FILES} > button'

    DISCOVERY_SCHEDULE_MODE_DDL_CSS = '.x-settings .x-select .x-select-trigger'
    DISCOVERY_SCHEDULE_REPEAT_INPUT_ID = 'system_research_date_recurrence'
    HISTORY_SCHEDULE_REPEAT_INPUT_ID = 'historical_schedule_recurrence'
    DISCOVERY_SCHEDULE_INTERVAL_INPUT_CSS = '#system_research_rate'
    DISCOVERY_SCHEDULE_MODE_OPTIONS = '.x-dropdown > .content .x-select-content > .x-select-options > *'
    HISTORY_ENABLED_CHECKBOX_TEXT = 'Enable scheduled historical snapshot'
    DISCOVERY_SCHEDULING_WRAPPING_CLASS = '.x-settings .item_discovery_settings'
    HISTORY_SCHEDULING_WRAPPING_CLASS = '.x-settings .item_history_settings'

    MIN_PASSWORD_LENGTH_ID = 'password_length'
    MIN_UPPERCASE_CHARS_ID = 'password_min_uppercase'
    MIN_LOWERCASE_CHARS_ID = 'password_min_lowercase'
    MIN_NUMBERS_CHARS_ID = 'password_min_numbers'
    MIN_SPECIAL_CHARS_ID = 'password_min_special_chars'

    CONNECTION_LABEL_REQUIRED_DIV_CSS = '#requireConnectionLabel .checkbox-container'
    CONNECTION_LABEL_REQUIRED_INPUT_CSS = '#requireConnectionLabel .checkbox-container input'

    ACTIVE_TAB = 'div.x-tab.active'

    ENTERPRISE_PASSWORD_MGMT_TEXT = 'Use Password Manager'
    ENTERPRISE_PASSWORD_MGMT_MODE_DDL = 'label[for=conditional] + div.x-select'
    ENTERPRISE_PASSWORD_MGMT_THYCOTIC_SS_TEXT = 'Thycotic Secret Server'
    ENTERPRISE_PASSWORD_MGMT_CYBERARK_VAULT_TEXT = 'CyberArk Vault'
    ENTERPRISE_PASSWORD_MGMT_AWS_SM_VAULT_TEXT = 'AWS Secrets Manager'

    SETTINGS_SAVE_TIMEOUT = 60 * 30
    ROLE_PANEL_CONTENT = '.role-panel.x-side-panel .ant-drawer-body .ant-drawer-body__content'
    ROLE_PANEL_TITLE_SELECTOR = '.role-panel .ant-drawer-title .title'
    ROLE_PANEL_ABSENT_CSS = '.role-panel.ant-drawer-open'
    USER_PANEL_ABSENT_CSS = '.user-panel.ant-drawer-open'
    SAVE_ROLE_NAME_SELECTOR = '.name-input'
    CSS_SELECTOR_ROLE_PANEL_ACTION_BY_NAME = '.role-panel .actions .action-{action_name}'
    CSS_SELECTOR_USER_PANEL_ACTION_BY_NAME = '.user-panel .actions .action-{action_name}'
    SAVE_ROLE_BUTTON = 'Save'
    ROLE_ROW_BY_NAME_XPATH = '//tr[child::td[.//text()=\'{role_name}\']]'
    USERNAME_ROW_BY_NAME_XPATH = '//tr[child::td[.//text()=\'{username}\']]'
    TABLE_ACTION_ITEM_XPATH = \
        '//li[@class=\'ant-dropdown-menu-item\' and contains(text(),\'{action}\')]'

    ABOUT_PAGE_LABEL_KEY_XPATH = '//div[@class=\'x-settings-about\']//label[@for=\'{value}\']'
    ABOUT_PAGE_LABEL_VALUE_XPATH = '//div[@class=\'x-settings-about\']//label[@for=\'{value}\']' \
                                   '/following-sibling::div[@class=\'table-td-content-{value}\']'
    ADD_USER_BUTTON_TEXT = 'Add User'
    ADD_ROLE_BUTTON_TEXT = 'Add Role'

    USE_S3_INTEGRATION = 'Enable Amazon S3 integration'
    USE_S3_BACKUP = 'Enable backup to Amazon S3'
    USE_ROOT_MASTER = 'Enable Root Master Mode'
    USE_PARALLEL_FETCH = 'Enable Parallel Adapters Fetch'

    FOOTER_ERROR_CSS = '.ant-drawer-body__footer .indicator-error--text'

    EXPANSION_HEADER_ICON_CSS = '.v-expansion-panel-header__icon'

    RESTRICTED_PERMISSIONS = {
        'dashboard': [
            'View dashboard',
        ]
    }

    VIEWER_PERMISSIONS = {
        'devices_assets': [
            'View devices',
        ],
        'users_assets': [
            'View users',
        ],
        'adapters': [
            'View adapters',
        ],
        'enforcements': [
            'View Enforcement Center',
            'View Enforcement Tasks'
        ],
        'reports': [
            'View reports',
        ],
        'instances': [
            'View instances',
        ],
        'dashboard': [
            'View dashboard',
        ],
    }

    VIEWER_ADDER_PERMISSIONS = {
        'devices_assets': [
            'View devices',
            'Create saved query',
        ],
        'users_assets': [
            'View users',
        ],
        'adapters': [
            'View adapters',
        ],
        'enforcements': [
            'View Enforcement Center',
            'Add Enforcement',
            'Edit Enforcement',
        ],
        'reports': [
            'View reports',
            'Add report',
        ],
        'instances': [
            'View instances',
        ],
        'dashboard': [
            'View dashboard',
            'Add chart',
        ],
    }

    AUTO_QUERY_CHECKBOX_ID = 'autoQuery'

    ONLY_REPORTS_PERMISSIONS = {
        'reports': 'all'
    }

    RESET_PASSWORD_FORM_CSS = '.reset-password__form'
    RESET_PASSWORD_FORM_EMAIL_INPUT_CSS = f'{RESET_PASSWORD_FORM_CSS} .email__input'
    SEND_EMAIL_BUTTON_TEXT = 'Send Email'
    PASSWORD_LINK_SEND_TOASTER = 'Password link was sent successfully'
    PASSWORD_LINK_COPY_TOASTER = 'Password link was copied to Clipboard'
    RESET_PASSWORD_MODAL_CLOSE_BUTTON_CSS = '.modal-header .x-button'
    RESET_PASSWORD_ACTION_ICON_CSS = '.action-reset-password'
    RESET_PASSWORD_COPY_TO_CLIPBOARD_ICON_CSS = '.copy-to-clipboard-icon'
    RESET_PASSWORD_LINK_INPUT_CSS = '.reset-link__input'

    CSV_DELIMITER_ID = 'cell_joiner'

    CLEAR_FEATURES_BUTTON_CSS = '.v-input__icon--clear'
    ENFORCEMENTS_FEATURE_TAG_TITLE = 'Enable Enforcement Center'
    ROLE_ASSIGNMENT_RULES_ROW = '.draggable > .item:nth-child({row_index})'
    LOCKED_ACTIONS_SELECT_ID = '#locked_actions_select'
    LIFECYCLE_WEEKDAYS_SELECT_ID = '#repeat_on_select'

    GUI_SETTINGS_DEFAULT_TIME_FORMAT = 'YYYY-MM-DD'
    GUI_SETTINGS_US_TIME_FORMAT = 'MM-DD-YYYY'

    ABOUT_PAGE_CONTRACT_EXPIRY_DATE_LABEL = 'Contract Expiry Date'
    ABOUT_PAGE_BUILD_DATE_LABEL = 'Build Date'

    ABOUT_PAGE_DATE_KEYS = [ABOUT_PAGE_BUILD_DATE_LABEL, ABOUT_PAGE_CONTRACT_EXPIRY_DATE_LABEL]
    NEXT_DAYS_COUNT = 30

    FEATURE_FLAG_BCRYPT_TO_PBKDF2_LABEL = ('Change local user password storage scheme from bcrypt to pbkdf2'
                                           ' ( federal mode only )')
    QUERIES_CACHE_TTL_CSS = '#ttl'

    @property
    def url(self):
        return f'{self.base_url}/settings'

    @property
    def root_page_css(self):
        return 'a#settings.item-link'

    def click_toggle_button(self,
                            toggle,
                            make_yes=True,
                            ignore_exc=False,
                            scroll_to_toggle=True,
                            window=TAB_BODY):
        return super().click_toggle_button(toggle=toggle,
                                           make_yes=make_yes,
                                           ignore_exc=ignore_exc,
                                           scroll_to_toggle=scroll_to_toggle,
                                           window=window)

    def click_global_settings(self):
        self.driver.find_element_by_css_selector(self.GLOBAL_SETTINGS_CSS).click()

    def click_certificate_settings(self):
        self.driver.find_element_by_css_selector(self.CERTIFICATE_SETTINGS_CSS).click()

    def click_lifecycle_settings(self):
        self.driver.find_element_by_css_selector(self.LIFECYCLE_SETTINGS_CSS).click()

    def click_manage_users_settings(self):
        time.sleep(1.5)
        self.driver.find_element_by_css_selector(self.MANAGE_USERS_CSS).click()
        self.wait_for_table_to_be_responsive()

    def click_manage_roles_settings(self):
        self.driver.find_element_by_css_selector(self.MANAGE_ROLES_CSS).click()
        self.wait_for_table_to_be_responsive()

    def get_role_panel_title(self):
        element = self.driver.find_element_by_css_selector(self.ROLE_PANEL_TITLE_SELECTOR)
        return element.text

    def is_users_and_roles_enabled(self):
        if len(self.driver.find_elements_by_css_selector(self.MANAGE_USERS_CSS)) == 0:
            return False
        if len(self.driver.find_elements_by_css_selector(self.MANAGE_ROLES_CSS)) == 0:
            return False
        return True

    def click_new_user(self):
        self.get_enabled_button(self.ADD_USER_BUTTON_TEXT).click()
        self.wait_for_config_user_panel()

    def wait_for_config_user_panel(self):
        self.wait_for_element_present_by_css('.x-side-panel.user-panel.ant-drawer-open',
                                             is_displayed=True)
        time.sleep(0.6)  # wait for animation

    def click_new_role(self):
        # wait for the panel animation
        time.sleep(2)
        self.get_enabled_button(self.ADD_ROLE_BUTTON_TEXT).click()
        # wait for the panel animation
        time.sleep(2)

    def assert_new_user_disabled(self):
        assert self.wait_for_element_present_by_xpath(
            self.DISABLED_BUTTON_XPATH.format(button_text=self.ADD_USER_BUTTON_TEXT))

    def get_new_role_enabled_button(self):
        return self.get_enabled_button(self.ADD_ROLE_BUTTON_TEXT)

    def assert_new_role_disabled(self):
        self.wait_for_element_present_by_xpath(
            self.DISABLED_BUTTON_XPATH.format(button_text=self.ADD_ROLE_BUTTON_TEXT))

    def click_edit_user(self, user_name):
        self.find_username_row_by_username(user_name).click()
        self.wait_for_config_user_panel()

    def fill_first_name(self, first_name):
        self.fill_text_field_by_css_selector('.first-name__input', first_name)

    def fill_new_user_details(self, username, password, first_name=None, last_name=None, role_name=None,
                              generate_password=False):
        self.fill_text_field_by_css_selector('.username__input', username)
        if generate_password:
            self.driver.find_element_by_css_selector('.auto-generated-password__input').click()
        else:
            self.fill_text_field_by_css_selector('.password__input', password)
        if first_name:
            self.fill_first_name(first_name)
        if last_name:
            self.fill_text_field_by_css_selector('.last-name__input', last_name)
        if role_name:
            self.select_role(role_name)

    def fill_edit_user_details(self, password=None, first_name=None, last_name=None):
        if password:
            self.fill_text_field_by_css_selector('.password__input', password)
        if first_name:
            self.fill_text_field_by_css_selector('.first-name__input', first_name)
        if last_name:
            self.fill_text_field_by_css_selector('.last-name__input', last_name)

    def fill_password_field(self, new_password):
        self.fill_text_field_by_css_selector('.password__input', new_password)

    def click_create_user(self):
        self.get_enabled_button(self.SAVE_USER_BUTTON).click()

    def click_create_role(self):
        self.scroll_into_view(self.get_enabled_button(self.SAVE_ROLE_BUTTON), self.ROLE_PANEL_CONTENT)
        self.get_enabled_button(self.SAVE_ROLE_BUTTON).click()

    def save_user_wait_done(self):
        self.get_enabled_button(self.SAVE_BUTTON).click()
        self.wait_for_user_updated_toaster()
        self.wait_for_user_panel_absent()

    def assert_create_user_disabled(self):
        self.wait_for_element_present_by_xpath(
            self.DISABLED_BUTTON_XPATH.format(button_text=self.SAVE_USER_BUTTON))

    def find_password_item(self):
        return self.driver.find_element_by_css_selector('.form__password')

    def _find_panel_action_by_name(self, css_selector, action_name):
        selector = css_selector.format(action_name=action_name)
        return WebDriverWait(self.driver, 2).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )

    def get_role_duplicate_panel_action(self):
        return self._find_panel_action_by_name(self.CSS_SELECTOR_ROLE_PANEL_ACTION_BY_NAME,
                                               action_name='duplicate')

    def get_role_remove_panel_action(self):
        return self._find_panel_action_by_name(self.CSS_SELECTOR_ROLE_PANEL_ACTION_BY_NAME,
                                               action_name='remove')

    def get_user_remove_panel_action(self):
        return self._find_panel_action_by_name(self.CSS_SELECTOR_USER_PANEL_ACTION_BY_NAME,
                                               action_name='remove')

    def assert_role_remove_button_missing(self):
        self.assert_element_absent_by_css_selector(self.CSS_SELECTOR_ROLE_PANEL_ACTION_BY_NAME
                                                   .format(action_name='remove'))

    def assert_user_remove_button_missing(self):
        self.assert_element_absent_by_css_selector(self.CSS_SELECTOR_USER_PANEL_ACTION_BY_NAME
                                                   .format(action_name='remove'))

    def get_role_edit_panel_action(self):
        return self._find_panel_action_by_name(self.CSS_SELECTOR_ROLE_PANEL_ACTION_BY_NAME,
                                               action_name='edit')

    def get_user_dialog_error(self):
        return self.driver.find_element_by_css_selector(self.ERROR_TEXT_CSS).text

    def add_user(self, username, password, first_name=None, last_name=None, role_name=None,
                 wait_for_toaster=True, generate_password=False):
        self.switch_to_page()
        self.click_manage_users_settings()
        self.wait_for_table_to_be_responsive()
        self.create_new_user(username, password, first_name, last_name, role_name, wait_for_toaster, generate_password)

    def create_new_user(self, username, password, first_name=None, last_name=None, role_name=None,
                        wait_for_toaster=True, generate_password=False, wait_for_side_panel_absence=True):
        self.wait_for_table_to_be_responsive()
        self.click_new_user()
        self.fill_new_user_details(username, password, first_name=first_name, last_name=last_name, role_name=role_name,
                                   generate_password=generate_password)
        self.click_create_user()
        if wait_for_toaster:
            self.wait_for_user_created_toaster()
        if wait_for_side_panel_absence:
            self.wait_for_user_panel_absent()

    def create_new_user_with_new_permission(self, username, password, first_name=None, last_name=None,
                                            permissions: dict = None):
        self.switch_to_page()
        self.click_manage_roles_settings()
        role_name = None
        if permissions:
            self.click_manage_roles_settings()
            role_name = f'{uuid4().hex[:15]} role'
            self.create_new_role(role_name, permissions)

        self.click_manage_users_settings()
        self.create_new_user(username, password, first_name, last_name, role_name)

    def create_new_role(self, name, permissions):
        self.click_new_role()
        self.wait_for_role_panel_present()
        self.fill_role_name(name)
        self.clear_permissions()
        self.select_permissions(permissions)

        self.click_create_role()
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS)
        self.wait_for_role_successfully_created_toaster()

    def clear_permissions(self):
        self.get_button('Expand All').click()
        for checkbox in self.find_elements_by_css('.v-expansion-panel-content .x-checkbox'):
            if self.is_toggle_has_selected_classes(checkbox):
                self.click_toggle_button(checkbox, make_yes=False)

    def select_permissions(self, permissions):
        for permissionCategory in permissions:
            categoryPanel = self.wait_for_element_present_by_css(f'.v-expansion-panel.{permissionCategory}')
            categoryIcon = categoryPanel.find_element_by_css_selector(self.EXPANSION_HEADER_ICON_CSS)
            if not self.is_element_clickable(categoryIcon):
                self.scroll_into_view(categoryIcon, self.ROLE_PANEL_CONTENT)
            if len(categoryPanel.find_elements_by_css_selector('.v-expansion-panel-header--active')) == 0:
                categoryPanel.find_element_by_css_selector(self.EXPANSION_HEADER_ICON_CSS).click()
            self.wait_for_element_present_by_css('.v-expansion-panel-header--active')
            permissionValues = permissions[permissionCategory]
            if permissionValues == 'all':
                categoryPanel.find_element_by_css_selector('.v-expansion-panel-header--active .x-checkbox').click()
            else:
                category_checkboxes = categoryPanel.find_elements_by_css_selector('.x-checkbox')
                category_checkboxes_by_text = {checkbox.text.strip(): checkbox for checkbox in category_checkboxes}
                for permissionValue in permissionValues:
                    self.click_toggle_button(category_checkboxes_by_text[permissionValue],
                                             make_yes=True,
                                             window=self.ROLE_PANEL_CONTENT)

    def duplicate_role(self, from_role_name, new_role_name):
        self.switch_to_page()
        self.click_manage_roles_settings()
        self.click_role_by_name(from_role_name)
        self.wait_for_role_panel_present()
        self.get_role_duplicate_panel_action().click()
        self.fill_role_name(new_role_name)
        self.click_create_role()
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS)
        self.wait_for_role_successfully_created_toaster()

    def update_role(self, role_name, permissions, users_has_this_role=False):
        self.switch_to_page()
        self.click_manage_roles_settings()
        self.wait_for_table_to_be_responsive()
        self.click_role_by_name(role_name)
        self.get_role_edit_panel_action().click()
        self.select_permissions(permissions)
        self.click_save_button()
        if users_has_this_role:
            self.safeguard_click_confirm('Yes')
        self.wait_for_role_successfully_saved_toaster()

    def wait_for_role_panel_present(self):
        self.wait_for_element_present_by_css(self.ROLE_PANEL_CONTENT, is_displayed=True)

    def wait_for_role_panel_absent(self):
        self.wait_for_element_absent_by_css(self.ROLE_PANEL_ABSENT_CSS)
        # Waiting for close animation
        time.sleep(1)

    def wait_for_user_panel_absent(self):
        self.wait_for_element_absent_by_css(self.USER_PANEL_ABSENT_CSS)
        # Waiting for close animation
        time.sleep(1)

    def match_role_permissions(self, name, permissions):
        self.click_role_by_name(name)
        self.wait_for_role_panel_present()

        categoryPanels = self.driver.find_elements_by_css_selector('.v-expansion-panel')
        for categoryPanel in categoryPanels:
            while len(categoryPanel.find_elements_by_css_selector('.v-expansion-panel-header--active')) == 0:
                self.scroll_into_view(categoryPanel.find_element_by_css_selector('.v-expansion-panel-header__icon'),
                                      self.ROLE_PANEL_CONTENT)
                categoryPanel.find_element_by_css_selector('.v-expansion-panel-header__icon').click()
            currentPermissionCategory = None
            for permissionCategoryName in permissions:
                if permissionCategoryName in categoryPanel.get_attribute('class'):
                    currentPermissionCategory = permissionCategoryName
            currentSelectedActions = categoryPanel. \
                find_elements_by_css_selector('.v-expansion-panel-content .x-checkbox.checked')
            if not currentPermissionCategory:
                continue
            if not currentSelectedActions or len(currentSelectedActions) != len(permissions[currentPermissionCategory]):
                self.close_role_panel()
                return False
            for currentSelectedAction in currentSelectedActions:
                selectedLabel = self.wait_for_element_present_by_css('.label',
                                                                     currentSelectedAction,
                                                                     is_displayed=True).text
                if selectedLabel not in permissions[currentPermissionCategory]:
                    self.close_role_panel()
                    return False
        self.close_role_panel()
        return True

    def find_username_row_by_username(self, username):
        return self.driver.find_element_by_xpath(self.USERNAME_ROW_BY_NAME_XPATH.format(username=username))

    def find_role_row_by_name(self, role_name):
        return self.driver.find_element_by_xpath(self.ROLE_ROW_BY_NAME_XPATH.format(role_name=role_name))

    def click_role_by_name(self, name):
        self.find_role_row_by_name(name).click()
        # wait for the panel animation
        time.sleep(0.5)
        self.wait_for_role_panel_present()

    def remove_role(self, name):
        self.click_role_by_name(name)
        self.get_role_remove_panel_action().click()
        self.wait_for_role_removed_successfully_toaster()

    def edit_user_wait_done(self, username, password=None, first_name=None, last_name=None, role_name=None):
        self.click_edit_user(username)
        self.fill_edit_user_details(password=password, first_name=first_name, last_name=last_name)
        if role_name:
            self.select_role(role_name)
        self.save_user_wait_done()

    def create_and_get_reset_password_link(self):
        self.click_reset_password_button()
        return self.get_reset_password_link()

    def edit_user_and_get_reset_password_link(self, username):
        self.click_edit_user(username)
        return self.create_and_get_reset_password_link()

    def click_reset_password_button(self):
        self.driver.find_element_by_css_selector(self.RESET_PASSWORD_ACTION_ICON_CSS).click()
        self.wait_for_element_present_by_css(self.MODAL_OVERLAY_CSS)
        time.sleep(0.6)  # Modal animation

    def get_reset_password_link(self):
        self.driver.find_element_by_css_selector(self.RESET_PASSWORD_COPY_TO_CLIPBOARD_ICON_CSS).click()
        self.wait_for_toaster(self.PASSWORD_LINK_COPY_TOASTER)
        return self.driver.find_element_by_css_selector(self.RESET_PASSWORD_LINK_INPUT_CSS).get_attribute('value')

    def close_reset_password_modal(self):
        self.driver.find_element_by_css_selector(self.RESET_PASSWORD_MODAL_CLOSE_BUTTON_CSS).click()

    def fill_email_and_click_reset_password_link(self, recipient):
        self.fill_text_by_element(
            self.driver.find_element_by_css_selector(self.RESET_PASSWORD_FORM_EMAIL_INPUT_CSS), recipient)
        self.click_button(self.SEND_EMAIL_BUTTON_TEXT)
        self.wait_for_toaster(self.PASSWORD_LINK_SEND_TOASTER)

    def wait_for_reset_password_form(self):
        self.wait_for_element_present_by_css(self.RESET_PASSWORD_FORM_CSS)

    def add_user_with_duplicated_role(self, username, password, first_name=None, last_name=None,
                                      role_to_duplicate: str = None):
        self.switch_to_page()
        role_name = None
        if role_to_duplicate:
            self.click_manage_roles_settings()
            role_name = f'{uuid4().hex[:15]} role'
            self.duplicate_role(role_to_duplicate, role_name)

        self.click_manage_users_settings()
        self.create_new_user(username, password, first_name, last_name, role_name)
        return role_name

    def get_all_user_names(self):
        return (x[0] for x in self.get_all_table_rows())

    def get_user_data_by_user_name(self, user_name):
        return self.get_specific_row_text_by_field_value('User Name', user_name)

    def get_user_object_by_user_name(self, user_name):
        User = self.get_users_object()
        row = self.get_specific_row_by_field_value('User Name', user_name)
        return User(*self.get_row_cells(row))

    def select_user_by_user_name(self, user_name):
        self.click_specific_row_checkbox('User Name', user_name)

    def remove_user_by_user_name_with_selection(self, user_name):
        self.select_user_by_user_name(user_name)
        self.click_button(self.ACTIONS_BUTTON,
                          button_class='user-management_actions__menu',
                          should_scroll_into_view=False)
        self.driver.find_element_by_xpath(self.TABLE_ACTION_ITEM_XPATH.format(action='Delete Users')).click()
        self.safeguard_click_confirm('Yes, Delete')

    def remove_user_by_user_name_with_user_panel(self, user_name):
        self.click_edit_user(user_name)
        self.wait_for_config_user_panel()
        self.get_user_remove_panel_action().click()
        self.safeguard_click_confirm('Yes, Delete')
        self.wait_for_user_removed_toaster()

    def change_disable_remember_me_toggle(self, make_yes):
        self.click_toggle_button(self.find_session_timeout_toggle(), make_yes=True, window=TAB_BODY)
        self.click_toggle_button(self.find_disable_remember_me_toggle(), make_yes=make_yes, scroll_to_toggle=True)

    def click_gui_settings(self):
        self.driver.find_element_by_css_selector(self.GUI_SETTINGS_CSS).click()

    def click_identity_providers_settings(self):
        self.driver.find_element_by_css_selector(self.IDENTITY_PROVIDERS_SETTINGS_CSS).click()

    def click_tunnel_settings(self):
        self.driver.find_element_by_css_selector(self.TUNNEL_SETTINGS_CSS).click()

    def click_feature_flags(self):
        self.driver.find_element_by_css_selector(self.FEATURE_FLAGS_CSS).click()

    def click_about(self):
        self.driver.find_element_by_css_selector(self.ABOUT_CSS).click()

    def is_save_button_disabled(self):
        return self.is_element_disabled(self.get_save_button())

    def click_save_button(self):
        self.get_save_button().click()

    def click_save_global_settings(self):
        self.click_generic_save_button('global-settings-save')

    def click_reset_to_defaults(self):
        self.find_elements_by_css('.actions-toggle')[0].click()
        time.sleep(1)
        self.driver.find_element_by_id('reset_to_defaults').click()
        self.click_modal_approve()

    def click_modal_approve(self):
        self.driver.find_element_by_id('approveId').click()

    def click_cancel_csr(self):
        self.find_element_parent_by_text('Cancel Pending Request').click()

    def get_modal_approve_button_status(self):
        return not self.is_element_disabled(self.driver.find_element_by_id('approveId'))

    def click_save_lifecycle_settings(self):
        self.click_generic_save_button('research-settings-save')

    def click_save_identity_providers_settings(self):
        self.click_generic_save_button('identity-providers-save')

    def click_save_gui_settings(self):
        self.click_generic_save_button('gui-settings-save')

    def click_save_manage_users_settings(self, selenium_user=None):
        parent = self.driver if selenium_user is None else selenium_user
        button = parent.find_element_by_id('user-settings-save')
        self.handle_button(button, scroll_into_view_container=self.TABS_BODY_CSS)

    def click_generic_save_button(self, button_id):
        self.click_button_by_id(button_id, scroll_into_view_container=self.TABS_BODY_CSS)

    def find_schedule_rate_error(self):
        return self.find_element_by_text('\'Repeat scheduled discovery every (hours)\' has an illegal value')

    def find_schedule_date_error(self):
        return self.find_element_by_text('\'Scheduled discovery time\' has an illegal value')

    def find_correlation_hours_error(self):
        return self.find_element_by_text(self.CORRELATION_HOUR_ERROR)

    def fill_schedule_rate(self, text):
        self.fill_text_field_by_css_selector(self.DISCOVERY_SCHEDULE_INTERVAL_INPUT_CSS, text)

    def get_schedule_rate_value(self):
        return self.driver.find_element_by_css_selector(self.SCHEDULE_RATE_CSS).get_attribute('value')

    def find_send_emails_toggle(self):
        return self.find_toggle_with_label_by_label(self.SEND_EMAILS_LABEL)

    def find_disable_remember_me_toggle(self):
        return self.find_checkbox_by_label_with_single_quote(self.DISABLE_REMEMBER_ME)

    def find_getting_started_toggle(self):
        return self.find_toggle_with_label_by_label(self.GETTING_STARTED_LABEL)

    def open_import_key_and_cert_modal(self):
        try:
            self.find_elements_by_css('.actions-toggle')[0].click()
        except ElementClickInterceptedException:
            pass
        time.sleep(1)
        try:
            self.driver.find_element_by_id('import_cert_and_key').click()
        except ElementClickInterceptedException:
            pass
        except ElementNotInteractableException:
            pass

    def open_generate_csr_modal(self):
        self.find_elements_by_css('.actions-toggle')[0].click()
        time.sleep(0.5)
        self.driver.find_element_by_id('generate_csr').click()

    def open_import_sign_csr_modal(self):
        self.find_elements_by_css('.actions-toggle')[0].click()
        time.sleep(0.5)
        self.driver.find_element_by_id('import_csr').click()

    def set_global_ssl_settings(self, hostname: str, cert_data, private_data):
        self.open_import_key_and_cert_modal()
        self.fill_text_field_by_element_id('hostname', hostname)
        cert_element = self.driver.find_element_by_css_selector(self.CERT_ELEMENT_SELECTOR)
        self.upload_file_on_element(cert_element, cert_data)

        private_element = self.driver.find_element_by_css_selector(self.PRIVATE_ELEMENT_SELECTOR)
        self.upload_file_on_element(private_element, private_data)

    def get_global_ssl_settings(self):
        cert = self.driver.find_element_by_css_selector(self.CERT_ELEMENT_FILENAME_SELECTOR).text
        private = self.driver.find_element_by_css_selector(self.PRIVATE_ELEMENT_FILENAME_SELECTOR).text
        return cert, private

    def toggle_advanced_settings(self):
        self.click_ant_collapse_panel_header(self.GLOBAL_SETTINGS_ADVANCED_SETTINGS_LABEL,
                                             scroll_into_view_container=self.TABS_BODY_CSS)
        time.sleep(0.5)
        self.scroll_into_view(self.driver.find_element_by_css_selector('.x-maintenance .x-content'), self.TABS_BODY_CSS)

    def find_remote_support_toggle(self):
        try:
            return self.find_checkbox_with_label_by_label(self.REMOTE_SUPPORT_LABEL)
        except NoSuchElementException:
            # The above is new behaviour and will not work on versions up to 1.15
            # Rollback to previous behaviour
            return self.find_checkbox_by_label(self.REMOTE_SUPPORT_LABEL_OLD)

    def find_analytics_toggle(self):
        try:
            return self.find_checkbox_with_label_by_label(self.ANALYTICS_LABEL)
        except NoSuchElementException:
            # The above is new behaviour and will not work on versions up to 1.15
            # Rollback to previous behaviour
            return self.find_checkbox_by_label(self.ANALYTICS_LABEL_OLD)

    def find_provision_toggle(self):
        return self.find_checkbox_with_label_by_label(self.PROVISION_LABEL)

    def find_syslog_toggle(self):
        return self.find_toggle_with_label_by_label(self.USE_SYSLOG_LABEL)

    def set_password_policy_toggle(self, enable=True):
        password_policy_checkbox = self.find_toggle_with_label_by_label(self.ENFORCE_PASSWORD_POLICY)
        self.click_toggle_button(password_policy_checkbox, make_yes=enable)

    def restore_initial_password_policy(self):
        self.switch_to_page()
        self.click_global_settings()
        self.set_password_policy_toggle(False)
        self.click_save_global_settings()
        self.wait_for_saved_successfully_toaster()

    def find_password_expiration_toggle(self):
        return self.find_toggle_with_label_by_label(self.PASSWORD_EXPIRATION_LABEL)

    def fill_password_policy(self, password_length, min_lowercase, min_uppercase, min_numbers, min_special_chars):
        self.fill_text_field_by_element_id(self.MIN_PASSWORD_LENGTH_ID, password_length)
        self.fill_text_field_by_element_id(self.MIN_LOWERCASE_CHARS_ID, min_lowercase)
        self.fill_text_field_by_element_id(self.MIN_UPPERCASE_CHARS_ID, min_uppercase)
        self.fill_text_field_by_element_id(self.MIN_NUMBERS_CHARS_ID, min_numbers)
        self.fill_text_field_by_element_id(self.MIN_SPECIAL_CHARS_ID, min_special_chars)

    def fill_password_expiration_days_field(self, days):
        self.fill_text_field_by_element_id(self.PASSWORD_EXPIRATION_FIELD_ID, days)

    def set_syslog_toggle(self, make_yes=True):
        self.click_toggle_button(self.find_syslog_toggle(), make_yes=make_yes, window=TAB_BODY)

    def select_syslog_ssl(self, text):
        self.select_option_without_search(self.SYSLOG_SSL_CSS_DROPBOX,
                                          self.SYSLOG_SSL_CSS_DROPBOX_OPTIONS,
                                          text)

    def find_should_history_be_gathered_toggle(self):
        return self.find_checkbox_by_label(self.HISTORY_GATHERED)

    def set_send_emails_toggle(self):
        toggle = self.find_send_emails_toggle()
        self.click_toggle_button(toggle, make_yes=True, scroll_to_toggle=False)

    def set_dont_send_emails_toggle(self):
        toggle = self.find_send_emails_toggle()
        self.click_toggle_button(toggle, make_yes=False, scroll_to_toggle=False)

    def set_remote_support_toggle(self, make_yes):
        self.set_maintenance_toggle(make_yes, self.find_remote_support_toggle())

    def set_analytics_toggle(self, make_yes):
        self.set_maintenance_toggle(make_yes, self.find_analytics_toggle())

    def set_provision_toggle(self, make_yes):
        self.set_maintenance_toggle(make_yes, self.find_provision_toggle())

    def set_maintenance_toggle(self, make_yes, toggle):
        self.click_toggle_button(toggle, make_yes=make_yes, scroll_to_toggle=False)
        try:
            self.confirm_maintenance_removal()
        except (NoSuchElementException, TimeoutException):
            # The above is new behaviour and will not work on versions up to 1.15
            # Rollback to previous behaviour
            self.save_and_wait_for_toaster()

    def confirm_maintenance_removal(self):
        self.wait_for_element_present_by_css(self.MODAL_OVERLAY_CSS)
        self.click_button(self.CONFIRM_BUTTON)
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS)

    def fill_syslog_host(self, host):
        self.fill_text_field_by_element_id(self.SYSLOG_HOST, host)

    def fill_syslog_port(self, port):
        self.fill_text_field_by_element_id(self.SYSLOG_PORT, port)

    def fill_email_port(self, port):
        self.fill_text_field_by_element_id(self.EMAIL_PORT_ID, port)

    def fill_email_host(self, host):
        self.fill_text_field_by_element_id(self.EMAIL_HOST_ID, host)

    def fill_fresh_service_domain(self, domain):
        self.fill_text_field_by_element_id(self.FRESH_SERVICE_DOMAIN, domain)

    def fill_fresh_service_api_key(self, key):
        self.fill_text_field_by_element_id(self.FRESH_SERVICE_API_KEY, key)

    def fill_fresh_service_email(self, email):
        self.fill_text_field_by_element_id(self.FRESH_SERVICE_ADMIN_EMAIL, email)

    def fill_saml_idp(self, idp):
        self.fill_text_field_by_element_id(self.SAML_IDP, idp)

    def fill_saml_metadata_url(self, metadata_url):
        self.fill_text_field_by_element_id(self.SAML_METADATA, metadata_url)

    def fill_saml_axonius_external_url(self, external_url):
        self.fill_text_field_by_element_id(self.SAML_AXONIUS_EXTERNAL_URL, external_url)

    def toggle_saml_auto_redirect(self, make_yes):
        toggle = self.find_checkbox_by_label(self.SAML_AUTO_REDIRECT_LABEL)
        self.click_toggle_button(toggle, make_yes=make_yes, window=TAB_BODY)

    def fill_session_timeout(self, timeout):
        self.fill_text_field_by_element_id(self.TIMEOUT_ID, timeout)

    def fill_csv_delimiter(self, delimiter):
        self.fill_text_field_by_element_id(self.CSV_DELIMITER_ID, delimiter)

    def find_email_port_error(self):
        return self.find_element_by_text('\'Port\' has an illegal value')

    def get_email_port(self):
        return self.driver.find_element_by_id(self.EMAIL_PORT_ID).get_attribute('value')

    def get_email_host(self):
        return self.driver.find_element_by_id(self.EMAIL_HOST_ID).get_attribute('value')

    def get_syslog_port(self):
        return self.driver.find_element_by_id(self.SYSLOG_PORT).get_attribute('value')

    def get_syslog_host(self):
        return self.driver.find_element_by_id(self.SYSLOG_HOST).get_attribute('value')

    def get_fresh_service_domain(self):
        return self.driver.find_element_by_id(self.FRESH_SERVICE_DOMAIN).get_attribute('value')

    def get_fresh_service_api_key(self):
        return self.driver.find_element_by_id(self.FRESH_SERVICE_API_KEY).get_attribute('value')

    def get_fresh_service_email(self):
        return self.driver.find_element_by_id(self.FRESH_SERVICE_ADMIN_EMAIL).get_attribute('value')

    def get_saml_idp(self):
        return self.driver.find_element_by_id(self.SAML_IDP).get_attribute('value')

    def wait_email_connection_failure_toaster(self, host):
        return self.wait_for_toaster(f'Could not connect to mail server "{host}"')

    def wait_for_saved_successfully_toaster(self, toaster_message=None):
        if toaster_message:
            self.wait_for_toaster(toaster_message)
        else:
            self.wait_for_toaster(self.SAVED_SUCCESSFULLY_TOASTER)

    def wait_for_role_successfully_created_toaster(self):
        self.wait_for_toaster(self.ROLE_SUCCESSFULLY_CREATED_TOASTER)

    def wait_for_role_successfully_saved_toaster(self):
        self.wait_for_toaster(self.ROLE_SUCCESSFULLY_SAVED_TOASTER)

    def wait_for_role_removed_successfully_toaster(self):
        self.wait_for_toaster(self.DELETED_ROLE_SUCCESSFULLY_TOASTER)

    def wait_for_user_created_toaster(self):
        self.wait_for_toaster('User created successfully')

    def wait_for_user_updated_toaster(self):
        self.wait_for_toaster('User updated successfully')

    def wait_for_user_updated_toaster_to_end(self):
        self.wait_for_toaster_to_end('User updated successfully')

    def wait_for_user_permissions_saved_toaster(self):
        self.wait_for_toaster('User permissions saved')

    def find_allow_ldap_logins_toggle(self):
        return self.find_toggle_with_label_by_label(self.LDAP_LOGINS_LABEL)

    def find_exact_search_toggle(self):
        return self.find_checkbox_by_label(self.EXACT_SEARCH_LABEL)

    def find_activate_bandicoot_toggle(self):
        self.wait_for_element_present_by_xpath(
            self.CHECKBOX_XPATH_TEMPLATE.format(label_text=self.ACTIVATE_BANDICOOT_LABEL))
        return self.find_checkbox_by_label(self.ACTIVATE_BANDICOOT_LABEL)

    def find_allow_okta_logins_toggle(self):
        return self.find_checkbox_by_label(self.OKTA_LOGINS_LABEL)

    def find_notify_on_adapters_fetch_toggle(self):
        return self.find_checkbox_by_label(self.NOTIFY_ON_ADAPTERS_FETCH_LABEL)

    def fill_dc_address(self, dc_address):
        self.fill_text_field_by_element_id(self.DC_ADDRESS, dc_address)

    def fill_group_ldap(self, group):
        self.fill_text_field_by_element_id(self.GROUP_CN, group)

    def fill_okta_login_details(self, client_id, client_secret, url, gui2_url=None, gui_url=None):
        self.fill_text_field_by_element_id('client_id', client_id)
        self.fill_text_field_by_element_id('client_secret', client_secret)
        self.fill_text_field_by_element_id('url', url)
        if gui2_url:
            self.fill_text_field_by_element_id('gui2_url', gui2_url)
        # to be removed after 1.15
        if gui_url:
            self.fill_text_field_by_element_id('gui_url', gui_url)

    def get_dc_address(self):
        return self.driver.find_element_by_id(self.DC_ADDRESS).get_attribute('value')

    def get_okta_login_details(self):
        return {
            'client_id': self.driver.find_element_by_id('client_id').get_attribute('value'),
            'client_secret': self.driver.find_element_by_id('client_secret').get_attribute('value'),
            'url': self.driver.find_element_by_id('url').get_attribute('value'),
            'gui2_url': self.driver.find_element_by_id('gui2_url').get_attribute('value')
        }

    def select_values_count_per_column(self, values_count_per_column):
        self.select_option_without_search(self.VALUES_COUNT_PER_COLUMN_DROPDOWN_CSS,
                                          self.SELECT_OPTION_CSS, values_count_per_column)

    def find_values_count_per_column(self):
        x = self.driver.find_element_by_css_selector(self.VALUES_COUNT_PER_COLUMN_DROPDOWN_CSS)
        return int(x.find_element_by_css_selector('.trigger-text').text)

    def select_values_count_entities_per_column(self, values_count_per_column):
        self.select_option_without_search(self.VALUES_COUNT_ENTITIES_PER_PAGE_CSS,
                                          self.SELECT_OPTION_CSS, values_count_per_column)

    def find_entities_count_per_page(self):
        x = self.driver.find_element_by_css_selector(self.VALUES_COUNT_ENTITIES_PER_PAGE_CSS)
        return int(x.find_element_by_css_selector('.trigger-text').text)

    def set_email_ssl_files(self, ca_data, cert_data, private_data):
        self.upload_file_by_id('ca_file', ca_data)
        self.upload_file_by_id('cert_file', cert_data)
        self.upload_file_by_id('private_key', private_data)

    def set_email_ssl_verification(self, verification_status):
        self.driver.find_element_by_css_selector('[for=use_ssl]+div>div>div>div').click()
        self.fill_text_field_by_css_selector('input.input-value', verification_status)
        self.driver.find_element_by_css_selector(self.SELECT_OPTION_CSS).click()

    def set_default_role_id(self, default_role_name):
        self.driver.find_element_by_css_selector('[for=default_role_id]+div>div>div>div').click()
        self.fill_text_field_by_css_selector('input.input-value', default_role_name)
        self.driver.find_element_by_css_selector(self.SELECT_OPTION_CSS).click()

    def click_start_remote_access(self):
        self.click_button('Start', scroll_into_view_container=PAGE_BODY)

    def click_stop_remote_access(self):
        self.click_button('Stop', scroll_into_view_container=PAGE_BODY)

    def save_and_wait_for_toaster(self, toaster_message=None):
        self.click_save_button()
        self.wait_for_saved_successfully_toaster(toaster_message=toaster_message)

    def assert_screen_is_restricted(self):
        assert len(self.driver.find_elements_by_css_selector('li.nav-item.disabled #settings')) == 1

    def get_permissions_text(self, label_text):
        return self.driver.find_element_by_xpath(
            self.DIV_BY_LABEL_TEMPLATE.format(label_text=label_text)). \
            find_element_by_css_selector('div > div'). \
            text

    def get_users_object(self):
        ui_headers = self.get_columns_header_text()
        return collections.namedtuple('User', ' '.join([header.lower().replace(' ', '_') for header in ui_headers]))

    def get_all_users_data(self):
        """
        :returns list of user objects, user object is a namedtuple, see _parse_user_row
        """
        ui_data = self.get_all_data_cells()

        User = self.get_users_object()

        return [User(*row) for row in ui_data]

    @staticmethod
    def get_permission_category_classes():
        labels = ('adapters',
                  'devices_assets',
                  'users_assets',
                  'enforcements',
                  'reports',
                  'settings',
                  'instances',
                  'compliance',
                  'dashboard')
        return labels

    @staticmethod
    def get_permission_labels():
        labels = ('Adapters',
                  'Devices',
                  'Users',
                  'Enforcements',
                  'Reports',
                  'Settings',
                  'Instances')
        return labels

    def click_remove_user(self):
        self.click_button_by_id('user-settings-remove')

    def click_confirm_remove_user(self):
        self.click_button('Remove User')

    def wait_for_user_removed_toaster(self):
        self.wait_for_toaster('Users removed.')

    def remove_user(self):
        self.click_remove_user()
        self.click_confirm_remove_user()
        self.wait_for_user_removed_toaster()

    def click_roles_button(self):
        self.click_button_by_id('config-roles')

    def find_default_role(self):
        return self.driver.find_element_by_css_selector('div.roles-default')

    def assert_default_role_is_restricted(self):
        self.find_default_role().find_element_by_css_selector('div[title="Restricted"]')

    def find_role_item(self):
        return self.driver.find_element_by_css_selector('.form__role')

    def find_role_dropdown(self):
        return self.driver.find_element_by_css_selector(self.SELECT_ROLE_CSS)

    def assert_placeholder_is_new(self):
        assert self.find_role_dropdown().find_element_by_css_selector('div.placeholder').text == 'NEW'

    def select_default_role(self, role_name):
        self.select_option_without_search('.all-roles', self.SELECT_OPTION_CSS, role_name)

    def select_role(self, role_text):
        self.driver.find_element_by_css_selector(self.SELECT_ROLE_CSS).click()
        self.wait_for_element_present_by_css(self.SELECT_ROLE_LIST_BOX_CSS, is_displayed=True)
        roles_list_box = self.driver.find_element_by_css_selector(self.SELECT_ROLE_LIST_BOX_CSS)
        self.find_element_by_text(role_text, roles_list_box).click()

    def fill_role_name(self, text):
        self.scroll_into_view(self.driver.find_element_by_css_selector('.name_input'),
                              self.ROLE_PANEL_CONTENT)
        self.fill_text_field_by_css_selector('.name_input', text)

    def click_done(self):
        self.click_button('Done')

    def wait_for_role_saved_toaster(self):
        self.wait_for_toaster('Role saved')

    def set_allow_saml_based_login(self, make_yes=True):
        toggle = self.find_toggle_with_label_by_label(self.SAML_LOGINS_LABEL)
        self.click_toggle_button(toggle, make_yes=make_yes, window=TAB_BODY)

    def is_saml_login_enabled(self):
        toggle = self.find_toggle_with_label_by_label(self.SAML_LOGINS_LABEL)
        return self.is_toggle_selected(toggle)

    def set_proxy_settings_enabled(self, make_yes=True):
        toggle = self.find_toggle_with_label_by_label(self.USE_PROXY)
        self.click_toggle_button(toggle, make_yes=make_yes, scroll_to_toggle=False)

    def set_vault_settings_enabled(self, make_yes=True):
        self.wait_for_element_present_by_text(self.ENTERPRISE_PASSWORD_MGMT_TEXT)
        toggle = self.find_toggle_with_label_by_label(self.USE_PASSWORD_MGR_VAULT)
        self.click_toggle_button(toggle, make_yes=make_yes, scroll_to_toggle=False)

    def set_gui_ssl_settings_enabled(self, make_yes=True):
        toggle = self.find_checkbox_by_label(self.USE_GUI_SSL)
        self.click_toggle_button(toggle, make_yes=make_yes, scroll_to_toggle=False)

    def set_correlation_schedule_settings_enabled(self, make_yes=True):
        toggle = self.find_toggle_with_label_by_label(self.USE_CORRELATION_SCHEDULE)
        self.click_toggle_button(toggle, make_yes=make_yes, scroll_to_toggle=True)

    def set_amazon_settings_enabled(self, make_yes=True):
        toggle = self.find_toggle_with_label_by_label(self.USE_AMAZON)
        self.click_toggle_button(toggle, make_yes=make_yes, scroll_to_toggle=True)

    def fill_bucket_name(self, bucket_name):
        self.fill_text_field_by_element_id(self.AMAZON_BUCKET_NAME_FIELD, bucket_name)

    def fill_correlation_hours_interval(self, correlation_hours_interval, key_down_tab=False):
        self.fill_text_field_by_element_id(CORRELATION_SCHEDULE_HOURS_INTERVAL, correlation_hours_interval)

    def fill_proxy_address(self, proxy_addr):
        self.fill_text_field_by_element_id('proxy_addr', proxy_addr)

    def fill_cyberark_domain_address(self, domain_addr):
        self.fill_text_field_by_element_id('domain', domain_addr)

    def fill_cyberark_port(self, port):
        self.fill_text_field_by_element_id('port', port)

    def fill_cyberark_application_id(self, application_id):
        self.fill_text_field_by_element_id('application_id', application_id)

    def fill_cyberark_cert_key(self, cert_file_content):
        self.upload_file_by_id('certificate_key', cert_file_content, is_bytes=True)

    def fill_proxy_port(self, port):
        self.fill_text_field_by_element_id('proxy_port', port)

    def fill_remote_access_timeout(self, timeout):
        self.fill_text_field_by_element_id('remote-access-timer', timeout)

    def is_locked_action(self, action_name):
        return action_name in self.get_locked_actions()

    def get_locked_actions(self):
        return self.get_multiple_select_selected_options_text(self.LOCKED_ACTIONS_SELECT_ID)

    def set_locked_actions(self, action_name):
        self.select_multiple_option_without_search(self.LOCKED_ACTIONS_SELECT_ID,
                                                   self.ANT_SELECT_MENU_ITEM_CSS,
                                                   [action_name])

    def unset_locked_actions(self, action_name):
        self.unselect_multiple_option_without_search(self.LOCKED_ACTIONS_SELECT_ID,
                                                     [action_name])

    def fill_trial_expiration_by_remainder(self, days_remaining=None):
        element = self.find_elements_by_xpath(self.XPATH_BY_CLASS_NAME.format(name=self.DATEPICKER_CLASS_NAME))[0]
        try:
            self.clear_existing_date(context=element)
        except NoSuchElementException:
            pass
        if days_remaining is not None:
            self.fill_datepicker_date(datetime.now() + timedelta(days_remaining), parent=element)

    def fill_contract_expiration_by_remainder(self, days_remaining=None, server_time=None):
        elements = self.find_elements_by_xpath(self.XPATH_BY_CLASS_NAME.format(name=self.DATEPICKER_CLASS_NAME))
        try:
            self.clear_existing_date(context=elements[0])
            self.clear_existing_date(context=elements[1])
        except NoSuchElementException:
            pass
        if days_remaining is not None:
            self.fill_datepicker_date((datetime.now() + timedelta(days_remaining))
                                      if server_time is None else server_time + timedelta(days_remaining),
                                      parent=elements[1])

    def fill_compliance_expiration_by_remainder(self, days_remaining=None, server_time=None):
        element = self.find_elements_by_xpath(self.XPATH_BY_CLASS_NAME.format(name=self.DATEPICKER_CLASS_NAME))[2]
        try:
            self.clear_existing_date(context=element)
        except NoSuchElementException:
            pass
        if days_remaining is not None:
            self.fill_datepicker_date((datetime.now() + timedelta(days_remaining))
                                      if server_time is None else server_time + timedelta(days_remaining),
                                      parent=element)

    def add_email_server(self, host, port):
        self.switch_to_page()
        self.click_global_settings()
        self.click_toggle_button(self.find_send_emails_toggle(), make_yes=True, scroll_to_toggle=False)
        self.fill_email_host(host)
        self.fill_email_port(port)
        self.save_and_wait_for_toaster()

    def remove_email_server(self):
        self.switch_to_page()
        self.click_global_settings()
        self.click_toggle_button(self.find_send_emails_toggle(), make_yes=False, scroll_to_toggle=False)
        self.save_and_wait_for_toaster()

    def toggle_getting_started(self, status=True):
        self.switch_to_page()
        self.click_global_settings()
        self.click_toggle_button(self.find_getting_started_toggle(),
                                 make_yes=status,
                                 scroll_to_toggle=True,
                                 window=self.TABS_BODY_CSS)
        self.save_and_wait_for_toaster()

    def get_role_select_placeholder(self):
        return self.driver.find_element_by_css_selector(self.ROLE_PLACEHOLDER_CSS).text

    def disable_getting_started_feature(self):
        """
        Navigates to settings page, click the 'Global Settings' tab and uncheck
        the Getting Started checkbox
        """
        self.toggle_getting_started(status=False)

    def enable_getting_started_feature(self):
        """
        Navigates to settings page, click the 'Global Settings' tab and check
        the Getting Started checkbox
        """
        self.toggle_getting_started(status=True)

    def enable_custom_ca(self, make_yes=True):
        label = self.driver.find_element_by_xpath(self.CA_CERTIFICATE_ENABLED).text
        toggle = self.find_toggle_with_label_by_label(label)
        self.click_toggle_button(toggle, make_yes=make_yes)

    def disable_custom_ca(self):
        label = self.driver.find_element_by_xpath(self.CA_CERTIFICATE_ENABLED).text
        toggle = self.find_toggle_with_label_by_label(label)
        self.click_toggle_button(toggle, scroll_to_toggle=False, make_yes=False)

    def click_add_ca_cert(self):
        self.driver.find_element_by_css_selector(self.CA_ADD_CERT_BUTTON).click()

    def get_first_ca_cert_input_type(self):
        return self._get_ca_cert_element(1).find_element_by_id('0').get_attribute('type')

    def get_first_ca_cert_fields_info(self):
        return self.get_ca_cert_fields_info(1)

    def get_second_ca_cert_fields_info(self):
        return self.get_ca_cert_fields_info(2)

    def _get_ca_cert_element(self, ca_file_index: int):
        # first div is the test label
        return self.driver.find_element_by_css_selector(self.CA_CERTS_FILES.format(file_index=ca_file_index))

    def get_ca_cert_fields_info(self, ca_file_index: int):
        cert_info = self._get_ca_cert_element(ca_file_index)
        if cert_info and cert_info.text:
            return cert_info.text
        return None

    def upload_ca_cert_file(self, cert_data, ca_file_index=1):
        # CERT FILE :  Array start from 2 , file input id start from 0
        element = self._get_ca_cert_element(ca_file_index).find_element_by_id(str(ca_file_index - 1))
        self.upload_file_on_element(element, cert_data, is_bytes=True)

    def is_cert_file_item_deleted(self, ca_delete_index=1):
        selector = self.CA_CERT_DELETE_BUTTON.format(file_index=ca_delete_index)
        certs = self.driver.find_elements_by_css_selector(selector)

        if len(certs) == 0:
            return True
        return False

    def _ca_cert_delete(self, ca_delete_index=1):
        delete_button = self.driver.find_element_by_css_selector(
            self.CA_CERT_DELETE_BUTTON.format(file_index=ca_delete_index))
        delete_button.click()

    @staticmethod
    def assert_ca_file_name_after_upload(cert_info: str):
        file_name, file_x_label, choose_file_label, x_label = cert_info.split('\n')
        assert file_name != 'No file chosen'
        assert file_x_label == 'x'
        assert choose_file_label == 'Choose file'
        assert x_label == 'x'

    @staticmethod
    def assert_ca_file_before_upload(cert_info: str):
        file_name, choose_file_label, x_label = cert_info.split('\n')
        assert file_name == 'No file chosen'
        assert choose_file_label == 'Choose file'
        assert x_label == 'x'

    def assert_ca_cert_first_file_input_type(self):
        assert self.get_first_ca_cert_input_type() == 'file'

    def ca_cert_delete_first(self):
        self._ca_cert_delete()

    def ca_cert_delete_second(self):
        self._ca_cert_delete(ca_delete_index=2)

    def find_session_timeout_toggle(self):
        return self.find_toggle_with_label_by_label(self.SESSION_TIMEOUT_LABEL)

    def find_queries_cache_toggle(self):
        return self.find_toggle_with_label_by_label(self.QUERIES_CACHE_LABEL)

    def set_session_timeout(self, enabled, timeout):
        self.switch_to_page()
        self.click_gui_settings()
        self.click_toggle_button(self.find_session_timeout_toggle(), make_yes=enabled, window=TAB_BODY)
        if enabled:
            self.fill_session_timeout(timeout)
            self.save_and_wait_for_toaster()

    def set_exact_search(self, enable=True):
        self.switch_to_page()
        self.click_gui_settings()
        self.wait_for_spinner_to_end()
        toggle = self.find_exact_search_toggle()
        self.click_toggle_button(toggle, make_yes=enable, scroll_to_toggle=True)
        self.click_save_button()
        self.wait_for_saved_successfully_toaster()

    def get_selected_discovery_mode(self):
        return self._find_discovery_mode_dropdown(self.DISCOVERY_SCHEDULE_MODE_DDL_CSS).text

    def get_discovery_mode_selected_item(self):
        return self._find_discovery_mode_dropdown(self.DISCOVERY_SCHEDULE_MODE_DDL_CSS).text

    def set_discovery_mode_dropdown_to_interval(self):
        if self.get_discovery_mode_selected_item() != self.SCHEDULE_INTERVAL_TEXT:
            self.select_option_without_search(self.DISCOVERY_SCHEDULE_MODE_DDL_CSS,
                                              self.SELECT_OPTION_CSS,
                                              self.SCHEDULE_INTERVAL_TEXT)

    def set_discovery__to_interval_value(self, interval=0, negative_flow=False):
        self._set_discovery_schedule_settings(mode=self.SCHEDULE_INTERVAL_TEXT,
                                              time_value=interval,
                                              negative_flow=negative_flow)

    def set_discovery__to_time_of_day(self, time_of_day=0, negative_flow=False):
        self._set_discovery_schedule_settings(mode=self.SCHEDULE_SCHEDULED_TEXT,
                                              time_value=time_of_day,
                                              negative_flow=negative_flow)

    # pylint: disable=dangerous-default-value
    def set_discovery__to_weekdays(self, time_of_day=0, weekdays: list = []):
        self._set_discovery_schedule_settings(mode=self.SCHEDULE_WEEKDAYS_TEXT,
                                              time_value=time_of_day,
                                              weekdays=weekdays)

    def set_history__to_every_cycle(self):
        self._set_history_schedule_settings(mode=self.SCHEDULE_EVERY_CYCLE)

    def set_history__to_time_of_day(self, time_of_day=0, negative_flow=False):
        self._set_history_schedule_settings(mode=self.SCHEDULE_SCHEDULED_TEXT,
                                            time_value=time_of_day,
                                            negative_flow=negative_flow)

    def set_history__to_weekdays(self, time_of_day=0, weekdays: list = []):
        self._set_history_schedule_settings(mode=self.SCHEDULE_WEEKDAYS_TEXT,
                                            time_value=time_of_day,
                                            weekdays=weekdays)

    def get_date_format(self):
        return self.find_elements_by_css(self.DATE_FORMAT_CSS)[0].text

    def set_date_format(self, date_format):
        self.select_option_without_search(self.DATE_FORMAT_CSS,
                                          self.SELECT_OPTION_CSS,
                                          date_format)

    def set_mutual_tls(self, certificate_file_content):
        self.find_toggle_with_label_by_label('Enable mutual TLS').click()
        mutual_tls_cert_element = self.find_elements_by_css(self.MUTUAL_TLS_CERTIFICATE_SELECTOR)[0]
        fname = self.upload_file_on_element(mutual_tls_cert_element, certificate_file_content, is_bytes=True)
        return fname

    def set_enforce_mutual_tls(self):
        self.find_checkbox_by_label('Enforce client certificate validation').click()

    def set_csv_delimiter(self, delimiter):
        self.switch_to_page()
        self.click_gui_settings()
        self.fill_csv_delimiter(delimiter)
        self.click_save_gui_settings()

    def clear_lifecycle_weekdays(self):
        self.unselect_multiple_option_without_search(self.LIFECYCLE_WEEKDAYS_SELECT_ID, values=list(WEEKDAYS))
        time.sleep(1)

    # pylint: disable=dangerous-default-value
    def _set_discovery_schedule_settings(self, mode='', time_value=0, negative_flow=False, weekdays: list = []):
        self.switch_to_page()
        self._set_schedule_settings(mode=mode, time_value=time_value, weekdays=weekdays, negative_flow=negative_flow,
                                    scheduling_wrapping_class=self.DISCOVERY_SCHEDULING_WRAPPING_CLASS,
                                    scheduling_repeat_selector=self.DISCOVERY_SCHEDULE_REPEAT_INPUT_ID)

    def _set_history_schedule_settings(self, mode='', time_value=0, negative_flow=False, weekdays: list = []):
        self.switch_to_page()
        self._set_schedule_settings(mode=mode, time_value=time_value, weekdays=weekdays, negative_flow=negative_flow,
                                    scheduling_wrapping_class=self.HISTORY_SCHEDULING_WRAPPING_CLASS,
                                    scheduling_repeat_selector=self.HISTORY_SCHEDULE_REPEAT_INPUT_ID)

    def _set_schedule_settings(self, mode='', time_value=0, negative_flow=False, weekdays: list = [],
                               scheduling_wrapping_class=None, scheduling_repeat_selector=None):
        self.switch_to_page()
        self.set_discovery_schedule_settings(mode=mode, time_value=time_value, weekdays=weekdays,
                                             scheduling_wrapping_class=scheduling_wrapping_class,
                                             scheduling_repeat_selector=scheduling_repeat_selector)
        if negative_flow:
            # click to get error message display
            self.click_save_button()
            assert self.is_save_button_disabled()
        else:
            self.save_and_wait_for_toaster()

    def get_connection_label_required_value(self):
        self.switch_to_page()
        self.click_gui_settings()
        return self.driver.find_element_by_css_selector(self.CONNECTION_LABEL_REQUIRED_INPUT_CSS).is_selected()

    def toggle_connection_label_required(self):
        self.switch_to_page()
        self.click_gui_settings()
        self.driver.find_element_by_css_selector(self.CONNECTION_LABEL_REQUIRED_DIV_CSS).click()

    def close_role_panel(self):
        self.close_side_panel()
        self.wait_for_role_panel_absent()

    def close_user_panel(self):
        self.close_side_panel()
        self.wait_for_user_panel_absent()

    def save_system_interval_schedule_settings(self, interval_value):
        self.test_base.axonius_system.gui.login_user(DEFAULT_USER)
        current_settings = self.test_base.axonius_system.gui.get_current_schedule_settings(self.SETTINGS_SAVE_TIMEOUT)
        if current_settings is not None:
            current_settings['discovery_settings']['system_research_rate'] = interval_value
            current_settings['discovery_settings']['conditional'] = 'system_research_rate'

        result = self.test_base.axonius_system.gui.save_system_interval_schedule_settings(
            current_settings,
            timeout=self.SETTINGS_SAVE_TIMEOUT)
        return result

    def open_discovery_mode_options(self):
        self.driver.find_element_by_css_selector(self.DISCOVERY_SCHEDULE_MODE_DDL_CSS).click()

    def find_discovery_mode_options(self):
        return self.driver.find_elements_by_css_selector(self.DISCOVERY_SCHEDULE_MODE_OPTIONS)

    def find_enterprise_password_mgmt_mode_dropdown(self):
        self.wait_for_element_present_by_css(self.ENTERPRISE_PASSWORD_MGMT_MODE_DDL)
        return self.driver.find_element_by_css_selector(self.ENTERPRISE_PASSWORD_MGMT_MODE_DDL)

    def get_enterprise_password_mgmt_settings_selected_item(self):
        return self.find_enterprise_password_mgmt_mode_dropdown().text

    def select_enterprise_password_mgmt_provider(self, vault_provider_text):
        if self.get_enterprise_password_mgmt_settings_selected_item() != vault_provider_text:
            self.select_option_without_search(self.ENTERPRISE_PASSWORD_MGMT_MODE_DDL,
                                              self.SELECT_OPTION_CSS,
                                              vault_provider_text)

    def select_thycotic_secret_server(self):
        self.select_enterprise_password_mgmt_provider(
            vault_provider_text=self.ENTERPRISE_PASSWORD_MGMT_THYCOTIC_SS_TEXT)

    def select_cyberark_secret_server(self):
        self.select_enterprise_password_mgmt_provider(
            vault_provider_text=self.ENTERPRISE_PASSWORD_MGMT_CYBERARK_VAULT_TEXT)

    def select_aws_secrets_manager(self):
        self.select_enterprise_password_mgmt_provider(
            vault_provider_text=self.ENTERPRISE_PASSWORD_MGMT_AWS_SM_VAULT_TEXT)

    def assert_server_error(self, error):
        assert self.wait_for_element_present_by_css(self.FOOTER_ERROR_CSS).text == error

    def wait_for_system_research_interval(self):
        self.wait_for_element_present_by_css(self.SCHEDULE_RATE_CSS)

    def fill_thycotic_host(self, host):
        self.fill_text_field_by_element_id('host', host)

    def fill_thycotic_port(self, port):
        self.fill_text_field_by_element_id('port', port)

    def fill_thycotic_username(self, username):
        self.fill_text_field_by_element_id('username', username)

    def fill_thycotic_password(self, password):
        self.fill_text_field_by_element_id('password', password)

    def fill_aws_access_key_id(self, access_key_id):
        self.fill_text_field_by_element_id(AWS_SM_ACCESS_KEY_ID, access_key_id)

    def fill_aws_secret_access_key(self, secret_access_key):
        self.fill_text_field_by_element_id(AWS_SM_SECRET_ACCESS_KEY, secret_access_key)

    def fill_aws_region(self, region):
        self.fill_text_field_by_element_id(AWS_SM_REGION, region)

    def clear_enterprise_password_mgmt_settings(self):
        self.switch_to_page()
        self.click_global_settings()
        self.wait_for_element_present_by_text(self.ENTERPRISE_PASSWORD_MGMT_TEXT)
        toggle = self.find_toggle_with_label_by_label(self.USE_PASSWORD_MGR_VAULT)
        self.click_toggle_button(toggle, make_yes=False, scroll_to_toggle=False)
        self.click_save_global_settings()

    def enable_thycotic_vault_global_config(self, thycotic_config: dict):
        self.switch_to_page()
        self.click_global_settings()
        self.set_vault_settings_enabled()
        self.select_thycotic_secret_server()
        self.fill_thycotic_host(thycotic_config['host'])
        self.fill_thycotic_port(thycotic_config['port'])
        self.fill_thycotic_username(thycotic_config['username'])
        self.fill_thycotic_password(thycotic_config['password'])
        self.click_save_global_settings()
        self.wait_for_saved_successfully_toaster()

    def enable_aws_vault_global_config(self, aws_config: dict):
        self.switch_to_page()
        self.click_global_settings()
        self.set_vault_settings_enabled()
        self.select_aws_secrets_manager()
        self.fill_aws_access_key_id(aws_config['access_key_id'])
        self.fill_aws_secret_access_key(aws_config['secret_access_key'])
        self.fill_aws_region(aws_config['region'])
        self.click_save_global_settings()
        self.wait_for_saved_successfully_toaster()

    def toggle_root_master(self, toggle_value):
        self.wait_for_element_present_by_text(self.USE_ROOT_MASTER)
        toggle = self.find_toggle_with_label_by_label(self.USE_ROOT_MASTER)
        self.click_toggle_button(toggle, make_yes=toggle_value, scroll_to_toggle=False)

    def toggle_parallel_fetch(self, toggle_value):
        toggle = self.find_toggle_with_label_by_label(self.USE_PARALLEL_FETCH)
        self.click_toggle_button(toggle, make_yes=toggle_value, scroll_to_toggle=False)

    def set_s3_integration_settings_enabled(self):
        toggle = self.find_toggle_with_label_by_label(self.USE_S3_INTEGRATION)
        self.click_toggle_button(toggle, make_yes=True, scroll_to_toggle=False)

    def set_s3_integration_settings_disabled(self):
        toggle = self.find_toggle_with_label_by_label(self.USE_S3_INTEGRATION)
        self.click_toggle_button(toggle, make_yes=False, scroll_to_toggle=False)

    def set_s3_backup_settings_enabled(self, make_yes=True):
        toggle = self.find_checkbox_by_label(self.USE_S3_BACKUP)
        self.click_toggle_button(toggle, make_yes=make_yes, scroll_to_toggle=False)

    def fill_s3_bucket_name(self, value):
        self.fill_text_field_by_element_id('bucket_name', value)

    def fill_s3_access_key(self, value):
        self.fill_text_field_by_element_id('aws_access_key_id', value)

    def fill_s3_secret_key(self, value):
        self.fill_text_field_by_element_id('aws_secret_access_key', value)

    def fill_s3_preshared_key(self, value):
        self.fill_text_field_by_element_id('preshared_key', value)

    def toggle_auto_querying(self, make_yes=True):
        self.switch_to_page()
        self.click_gui_settings()
        toggle = self.driver.find_element_by_id(self.AUTO_QUERY_CHECKBOX_ID)
        self.click_toggle_button(toggle, make_yes=make_yes)
        self.save_and_wait_for_toaster()

    def disable_auto_querying(self):
        self.toggle_auto_querying(make_yes=False)

    def enable_auto_querying(self):
        self.toggle_auto_querying(make_yes=True)

    def toggle_compliance_visible_feature(self, show_feature):
        cloud_visible_toggle = self.find_toggle_with_label_by_label('Cloud Visible')
        self.click_toggle_button(cloud_visible_toggle, make_yes=show_feature)

    def toggle_compliance_enable_feature(self, show_feature):
        cloud_enabled_toggle = self.find_checkbox_by_label('Cloud Enabled')
        self.click_toggle_button(cloud_enabled_toggle, make_yes=show_feature)

    def enable_and_display_compliance(self):
        self.toggle_compliance_visible_feature(True)
        self.toggle_compliance_enable_feature(True)

    def toggle_enforcement_feature_tag(self, value):
        self.switch_to_page()
        self.click_feature_flags()
        cloud_visible_toggle = self.find_checkbox_by_label(self.ENFORCEMENTS_FEATURE_TAG_TITLE)
        self.click_toggle_button(cloud_visible_toggle, make_yes=value)
        self.save_and_wait_for_toaster()

    def set_evaluate_role_on_new_users_only(self):
        self.select_option_without_search(self.EVALUATE_ROLE_ASSIGNMENT_ON_DDL,
                                          self.SELECT_OPTION_CSS,
                                          'New users only')

    def set_evaluate_role_on_new_and_existing_users(self):
        self.select_option_without_search(self.EVALUATE_ROLE_ASSIGNMENT_ON_DDL,
                                          self.SELECT_OPTION_CSS,
                                          'New and existing users')

    def click_assignment_rule_collapse(self):
        self.driver.find_element_by_css_selector('.ant-collapse-header').click()
        self.wait_for_element_present_by_css('.ant-collapse-content-active')

    def click_add_assignment_rule(self):
        self.click_button('+', scroll_into_view_container=self.TABS_BODY_CSS)

    def fill_ldap_assignment_rule(self, rule_type, value, role_name, index=1):
        self.select_rule_type(rule_type, index)
        self.fill_rule_value(value, index)
        self.select_rule_role(role_name, index)

    def fill_saml_assignment_rule(self, key, value, role_name, index=1):
        self.fill_rule_key(key, index)
        self.fill_rule_value(value, index)
        self.select_rule_role(role_name, index)

    def select_rule_type(self, rule_type, index=1):
        rule_row = self.find_role_assignment_rule_row(index)
        self.select_option_without_search('.x-select', self.SELECT_OPTION_CSS, rule_type, rule_row)

    def fill_rule_key(self, key, index=1):
        rule_row = self.find_role_assignment_rule_row(index)
        self.fill_text_field_by_element_id('key', key, rule_row)

    def fill_rule_value(self, value, index=1):
        rule_row = self.find_role_assignment_rule_row(index)
        self.fill_text_field_by_element_id('value', value, rule_row)

    def select_rule_role(self, role_name, index=1):
        rule_row = self.find_role_assignment_rule_row(index)
        self.select_option_without_search('.all-roles', self.SELECT_OPTION_CSS, role_name, rule_row)

    def find_role_assignment_rule_row(self, index=1):
        return self.driver.find_element_by_css_selector(self.ROLE_ASSIGNMENT_RULES_ROW.format(row_index=index))

    def restore_feature_flags(self, restore_cloud_visible):
        self.switch_to_page()
        self.click_feature_flags()
        self.fill_trial_expiration_by_remainder(28)
        self.toggle_compliance_enable_feature(False)
        if restore_cloud_visible:
            self.toggle_compliance_visible_feature(False)
        self.save_and_wait_for_toaster()

    def toggle_compliance_feature(self):
        self.switch_to_page()
        self.click_feature_flags()
        self.enable_and_display_compliance()
        self.save_and_wait_for_toaster()

    def save_daily_historical_snapshot(self, enable=True):
        self.switch_to_page()
        toggle = self.find_toggle_with_label_by_label(self.HISTORY_ENABLED_CHECKBOX_TEXT)
        self.click_toggle_button(toggle, make_yes=enable)
        self.save_and_wait_for_toaster()

    def set_saml_auto_redirect(self, make_yes=True):
        self.switch_to_page()
        self.click_identity_providers_settings()
        self.toggle_saml_auto_redirect(make_yes)
        self.click_save_identity_providers_settings()
        self.wait_for_saved_successfully_toaster()

    def set_saml(self, name, metadata_url, external_url='', default_role_name=None,
                 evaluate_new_and_existing_users=False, assignment_rules=None):
        if assignment_rules is None:
            assignment_rules = []
        self.switch_to_page()
        self.click_identity_providers_settings()
        self.set_allow_saml_based_login()
        self.fill_saml_idp(name)
        self.fill_saml_metadata_url(metadata_url)
        self.fill_saml_axonius_external_url(external_url=external_url)
        if default_role_name:
            self.set_default_role_id(default_role_name)
        if evaluate_new_and_existing_users or len(assignment_rules) > 0:
            if evaluate_new_and_existing_users:
                self.set_evaluate_role_on_new_and_existing_users()
            else:
                self.set_evaluate_role_on_new_users_only()
            for assignment_rule in assignment_rules:
                self.click_add_assignment_rule()
                self.fill_saml_assignment_rule(
                    assignment_rule.get('key'), assignment_rule.get('value'), assignment_rule.get('role'))

        self.click_save_identity_providers_settings()
        self.wait_for_saved_successfully_toaster()

    def fetch_saml_user(self):
        all_users = self.get_all_users_data()
        valid_users = [u for u in all_users if u.source.lower() == 'saml']
        assert len(valid_users) == 1, 'Got more or less than expected valid saml usernames'
        return valid_users[0]

    def wait_for_tunnel_disconnected_modal(self):
        self.wait_for_element_present_by_css('.tunnel-modal', is_displayed=True)

    def close_tunnel_disconnected_modal(self):
        self.wait_for_element_present_by_css('.ant-modal-close-x').click()
        self.wait_for_modal_close()

    def clear_trial_datepicker(self):
        element = self.find_elements_by_css(self.TRIAL_DATE_PICKER_CSS)[0]
        try:
            self.clear_existing_date(element)
        except NoSuchElementException:
            pass

    def clear_contract_datepicker(self):
        element = self.find_elements_by_css(self.CONTRACT_DATE_PICKER_CSS)[0]
        try:
            self.clear_existing_date(element)
        except NoSuchElementException:
            pass

    def about_page_get_label_text(self, label_value):
        element = self.find_element_by_xpath(self.ABOUT_PAGE_LABEL_KEY_XPATH.format(value=label_value))
        return element.text

    def about_page_get_label_value_by_key(self, label_key):
        element = self.find_element_by_xpath(self.ABOUT_PAGE_LABEL_VALUE_XPATH.format(value=label_key))
        return element.text

    def about_page_contract_details_exists(self):
        try:
            return len(self.find_elements_by_text(self.ABOUT_PAGE_CONTRACT_EXPIRY_DATE_LABEL)) > 0
        except Exception:
            return False

    def assert_about_tab_values(self, metadata_file, date_format=GUI_SETTINGS_DEFAULT_TIME_FORMAT):
        for key, value in metadata_file:
            if value:
                assert key == self.about_page_get_label_text(key)
                if key in self.ABOUT_PAGE_DATE_KEYS:
                    date_str = datetime.date(dateutil.parser.parse(value))
                    assert date_str.strftime(
                        get_datetime_format_by_gui_date(date_format)) == self.about_page_get_label_value_by_key(key)
                else:
                    assert value == self.about_page_get_label_value_by_key(key)

    def find_bcrypt_to_pbkdf2_checkbox(self):
        return self.find_checkbox_by_label(self.FEATURE_FLAG_BCRYPT_TO_PBKDF2_LABEL)

    def toggle_bcrypt_to_pbkdf2_feature_flag(self, make_yes=True):
        self.click_toggle_button(self.find_bcrypt_to_pbkdf2_checkbox(), make_yes=make_yes)

    def verify_bcrypt_to_pbkdf2_forbidden_on_regular_build(self):
        self.switch_to_page()
        self.click_feature_flags()
        self.toggle_bcrypt_to_pbkdf2_feature_flag()
        # wait for failure toaster
        self.save_and_wait_for_toaster(toaster_message=ENABLE_PBKDF2_FED_BUILD_ONLY_ERROR)

    def verify_bcrypt_to_pbkdf2_status(self, status):
        self.switch_to_page()
        self.click_feature_flags()
        assert self.is_toggle_selected(self.driver.find_element_by_id(FeatureFlagsNames.EnablePBKDF2FedOnly)) == status

    def approve_queries_cache_safeguard(self):
        safeguard_modal = self.driver.find_element_by_css_selector(self.DIALOG_OVERLAY_ACTIVE_CSS)
        self.click_button(self.YES_BUTTON, context=safeguard_modal)
        self.wait_for_element_absent_by_css(self.DIALOG_OVERLAY_ACTIVE_CSS)

    def toggle_queries_cache(self, make_yes=True, ttl=None):
        self.switch_to_page()
        self.click_gui_settings()
        self.click_toggle_button(self.find_queries_cache_toggle(), make_yes=make_yes, window=TAB_BODY)
        if make_yes:
            # wait for modal to appear.
            time.sleep(1)
            self.approve_queries_cache_safeguard()
        if ttl:
            self.fill_text_field_by_css_selector(self.QUERIES_CACHE_TTL_CSS, ttl)
        self.save_and_wait_for_toaster()
