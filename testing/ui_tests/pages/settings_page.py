import time
import collections

from datetime import datetime, timedelta
from uuid import uuid4
import requests

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from axonius.consts.gui_consts import PROXY_ERROR_MESSAGE
from axonius.consts.plugin_consts import CORRELATION_SCHEDULE_HOURS_INTERVAL
from services.axon_service import TimeoutException
from ui_tests.pages.page import PAGE_BODY, TAB_BODY, Page


# pylint: disable=too-many-lines,no-member


class SettingsPage(Page):
    SCHEDULE_RATE_CSS = '#system_research_rate'
    DEFAULT_SCHEDULE_RATE = '12'
    DEFAULT_SCHEDILE_DATE = '13:00'
    GLOBAL_SETTINGS_CSS = 'li#global-settings-tab'
    GUI_SETTINGS_CSS = 'li#gui-settings-tab'
    LIFECYCLE_SETTINGS_CSS = 'li#research-settings-tab'
    MANAGE_USERS_CSS = 'li#user-settings-tab'
    MANAGE_ROLES_CSS = 'li#roles-settings-tab'
    FEATURE_FLAGS_CSS = 'li#feature-flags-tab'
    ABOUT_CSS = 'li#about-settings-tab'
    SEND_EMAILS_LABEL = 'Send emails'
    DISABLE_REMEMBER_ME = 'Disable \'Remember me\''
    SESSION_TIMEOUT_LABEL = 'Enable session timeout'
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
    LDAP_LOGINS_LABEL = 'Allow LDAP logins'
    OKTA_LOGINS_LABEL = 'Allow Okta logins'
    EXACT_SEARCH_LABEL = 'Use exact match for assets search'
    NOTIFY_ON_ADAPTERS_FETCH_LABEL = 'Notify on adapters fetch'
    SAML_LOGINS_LABEL = 'Allow SAML-based logins'
    TRIAL_MODE_FLAG_LABEL = 'Is trial mode'
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
    HISTORY_GATHERED = 'Enable daily historical snapshot'
    DC_ADDRESS = 'dc_address'
    GROUP_CN = 'group_cn'
    SINGLE_ADAPTER_VIEW = 'Use single adapter view'
    TABLE_MULTI_LINE_VIEW = 'Use table multi line view'
    ALLOW_GOOGLE_LOGINS = 'Allow Google logins'
    GOOGLE_CLIENT_ID_OLD = 'client_id'
    GOOGLE_CLIENT_ID = 'client'
    GOOGLE_EMAIL_OF_ADMIN = 'account_to_impersonate'
    READ_ONLY_PERMISSION = 'Read only'
    READ_WRITE_PERMISSION = 'Read and edit'
    RESTRICTED_PERMISSION = 'Restricted'
    SAVED_SUCCESSFULLY_TOASTER = 'Saved Successfully.'
    ROLE_SUCCESSFULLY_CREATED_TOASTER = 'Role created.'
    ROLE_SUCCESSFULLY_SAVED_TOASTER = 'Role saved.'
    DELETED_ROLE_SUCCESSFULLY_TOASTER = 'Role deleted.'
    SAVED_SUCCESSFULLY_PERMISSIONS_TOASTER = 'User permissions saved.'
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
    # sorry - but it's not my fault
    # https://axonius.atlassian.net/browse/AX-2991
    # those are the fully fledged css selectors for the elements
    CERT_ELEMENT_SELECTOR = 'div.x-tab.active.global-settings-tab' \
                            ' > .tab-settings > .x-form > .x-array-edit > div:nth-child(1) > div > div' \
                            ' > div:nth-child(4) > div > div > input[type="file"] '
    PRIVATE_ELEMENT_SELECTOR = 'div.x-tab.active.global-settings-tab' \
                               ' > .tab-settings > .x-form > .x-array-edit > div:nth-child(1) > div > div' \
                               ' > div:nth-child(5) > div > div > input[type="file"] '
    CERT_ELEMENT_FILENAME_SELECTOR = 'div.x-tab.active.global-settings-tab' \
                                     ' > .tab-settings > .x-form > .x-array-edit > div:nth-child(1) > div > div' \
                                     ' > div:nth-child(4) > div > div > div.file-name '
    PRIVATE_ELEMENT_FILENAME_SELECTOR = 'div.x-tab.active.global-settings-tab' \
                                        ' > .tab-settings > .x-form > .x-array-edit > div:nth-child(1) > div > div' \
                                        ' > div:nth-child(5) > div > div > div.file-name '

    LOCKED_ACTION_OPTION_XPATH = '//div[contains(@class, \'v-select\')]' \
                                 '//div[contains(@class, \'v-list-item\') and .//text()=\'{action_name}\']'

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

    CA_CERTS_FILES = 'div.x-array-edit > div:nth-child(2) > div > div >' \
                     ' div:nth-child(3) > div > div > div:nth-child({file_index})'

    CA_CERT_DELETE_BUTTON = f'{CA_CERTS_FILES} > button'

    DISCOVERY_SCHEDULE_MODE_DDL = '.x-settings .x-select .x-select-trigger'
    DISCOVERY_SCHEDULE_TIME_PICKER_INPUT_CSS = '.time-picker-text input'
    DISCOVERY_SCHEDULE_REPEAT_INPUT = 'system_research_date_recurrence'
    DISCOVERY_SCHEDULE_INTERVAL_INPUT_CSS = '#system_research_rate'
    DISCOVERY_SCHEDULE_INTERVAL_TEXT = 'Interval'
    DISCOVERY_SCHEDULE_SCHEDULED_TEXT = 'Scheduled'
    DISCOVERY_SCHEDULE_MODE_OPTIONS = '.x-dropdown > .content .x-select-content > .x-select-options > *'

    MIN_PASSWORD_LENGTH_ID = 'password_length'
    MIN_UPPERCASE_CHARS_ID = 'password_min_uppercase'
    MIN_LOWERCASE_CHARS_ID = 'password_min_lowercase'
    MIN_NUMBERS_CHARS_ID = 'password_min_numbers'
    MIN_SPECIAL_CHARS_ID = 'password_min_special_chars'

    CONNECTION_LABEL_REQUIRED_DIV_CSS = '#requireConnectionLabel .checkbox-container'
    CONNECTION_LABEL_REQUIRED_INPUT_CSS = '#requireConnectionLabel .checkbox-container input'
    ACTIVE_TAB = 'div.x-tab.active'

    ENTERPRISE_PASSWORD_MGMT_TEXT = 'Use Password Manager'
    ENTERPRISE_PASSWORD_MGMT_MODE_DDL = 'div > div > div:nth-child(3) > div > div'
    ENTERPRISE_PASSWORD_MGMT_MODE_DDL_OPTIONS = '.x-select-option'
    ENTERPRISE_PASSWORD_MGMT_THYCOTIC_SS_TEXT = 'Thycotic Secret Server'
    ENTERPRISE_PASSWORD_MGMT_CYBERARK_VAULT_TEXT = 'CyberArk Vault'

    SETTINGS_SAVE_TIMEOUT = 60 * 30
    ROLE_PANEL_CONTENT = '.role-panel .x-side-panel__content'
    USERS_PANEL_CONTENT = '.user-panel .v-navigation-drawer__content'
    SAVE_ROLE_NAME_SELECTOR = '.name-input'
    CSS_SELECTOR_ROLE_PANEL_ACTION_BY_NAME = '.role-panel .actions .action-{action_name}'
    CSS_SELECTOR_USER_PANEL_ACTION_BY_NAME = '.user-panel .actions .action-{action_name}'
    SAVE_ROLE_BUTTON = 'Save'
    ROLE_ROW_BY_NAME_XPATH = '//tr[child::td[.//text()=\'{role_name}\']]'
    USERNAME_ROW_BY_NAME_XPATH = '//tr[child::td[.//text()=\'{username}\']]'
    TABLE_ACTION_ITEM_XPATH = \
        '//li[@class=\'ant-dropdown-menu-item\' and contains(text(),\'{action}\')]'

    ADD_USER_BUTTON_TEXT = 'Add User'
    ADD_ROLE_BUTTON_TEXT = 'Add Role'

    USE_S3_INTEGRATION = 'Enable Amazon S3 integration'
    USE_S3_BACKUP = 'Enable backup to Amazon S3'
    USE_ROOT_MASTER = 'Enable Root Master Mode'

    FOOTER_ERROR_CSS = '.x-side-panel__footer .indicator-error--text'

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

    def click_lifecycle_settings(self):
        self.driver.find_element_by_css_selector(self.LIFECYCLE_SETTINGS_CSS).click()

    def click_manage_users_settings(self):
        self.driver.find_element_by_css_selector(self.MANAGE_USERS_CSS).click()

    def click_manage_roles_settings(self):
        self.driver.find_element_by_css_selector(self.MANAGE_ROLES_CSS).click()

    def is_users_and_roles_enabled(self):
        if len(self.driver.find_elements_by_css_selector(self.MANAGE_USERS_CSS)) == 0:
            return False
        if len(self.driver.find_elements_by_css_selector(self.MANAGE_ROLES_CSS)) == 0:
            return False
        return True

    def click_new_user(self):
        self.get_enabled_button(self.ADD_USER_BUTTON_TEXT).click()
        # wait for the panel animation
        time.sleep(2)

    def wait_for_new_user_panel(self):
        self.wait_for_element_present_by_css('.x-side-panel.user-panel.v-navigation-drawer--open',
                                             is_displayed=True)

    def click_new_role(self):
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
        # wait for the panel animation
        time.sleep(2)

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

    def click_update_user(self, wait_for_toaster=True):
        self.get_enabled_button(self.SAVE_BUTTON).click()
        if wait_for_toaster:
            self.wait_for_user_updated_toaster()

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

    def create_new_user(self, username, password, first_name=None, last_name=None, role_name=None,
                        wait_for_toaster=True, generate_password=False):
        self.wait_for_table_to_load()
        self.click_new_user()
        self.wait_for_new_user_panel()
        self.fill_new_user_details(username, password, first_name=first_name, last_name=last_name, role_name=role_name,
                                   generate_password=generate_password)
        self.click_create_user()
        if wait_for_toaster:
            self.wait_for_user_created_toaster()

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
                category_checkboxes_by_text = {checkbox.text: checkbox for checkbox in category_checkboxes}
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
        self.wait_for_table_to_load()
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
        self.wait_for_element_absent_by_css(self.ROLE_PANEL_CONTENT, is_displayed=True)

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
            currentSelectedActions = categoryPanel.\
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
        time.sleep(2)
        self.wait_for_role_panel_present()

    def remove_role(self, name):
        self.click_role_by_name(name)
        self.get_role_remove_panel_action().click()
        self.wait_for_role_removed_successfully_toaster()

    def update_new_user(self, username, password=None, first_name=None, last_name=None, role_name=None):
        self.click_edit_user(username)
        self.fill_edit_user_details(password=password, first_name=first_name, last_name=last_name)
        if role_name:
            self.select_role(role_name)
        self.click_update_user()
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS)

    def get_user_reset_password_link(self, username):
        self.click_edit_user(username)
        self.click_reset_password_button()
        return self.get_reset_password_link()

    def click_reset_password_button(self):
        self.driver.find_element_by_css_selector(self.RESET_PASSWORD_ACTION_ICON_CSS).click()
        self.wait_for_element_present_by_css(self.MODAL_OVERLAY_CSS)

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
        self.wait_for_new_user_panel()
        self.get_user_remove_panel_action().click()
        self.safeguard_click_confirm('Yes, Delete')
        self.wait_for_user_removed_toaster()

    def change_disable_remember_me_toggle(self, make_yes):
        self.click_toggle_button(self.find_session_timeout_toggle(), make_yes=True, window=TAB_BODY)
        self.click_toggle_button(self.find_disable_remember_me_toggle(), make_yes=make_yes, scroll_to_toggle=True)

    def click_gui_settings(self):
        self.driver.find_element_by_css_selector(self.GUI_SETTINGS_CSS).click()

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

    def click_save_lifecycle_settings(self):
        self.click_generic_save_button('research-settings-save')

    def click_save_gui_settings(self):
        self.click_generic_save_button('gui-settings-save')

    def click_save_manage_users_settings(self, selenium_user=None):
        parent = self.driver if selenium_user is None else selenium_user
        button = parent.find_element_by_id('user-settings-save')
        self.handle_button(button, scroll_into_view_container=self.TABS_BODY_CSS)

    def click_generic_save_button(self, button_id):
        self.click_button_by_id(button_id, scroll_into_view_container=self.TABS_BODY_CSS)

    def find_schedule_rate_error(self):
        return self.find_element_by_text('\'Hours between discovery cycles\' has an illegal value')

    def find_schedule_date_error(self):
        return self.find_element_by_text('\'Daily discovery time\' has an illegal value')

    def find_correlation_hours_error(self):
        return self.find_element_by_text(self.CORRELATION_HOUR_ERROR)

    def fill_schedule_rate(self, text):
        self.fill_text_field_by_css_selector(self.DISCOVERY_SCHEDULE_INTERVAL_INPUT_CSS, text)

    def fill_schedule_date(self, text):
        self.fill_text_field_by_css_selector(self.DISCOVERY_SCHEDULE_TIME_PICKER_INPUT_CSS, text)
        self.fill_text_field_by_element_id(self.DISCOVERY_SCHEDULE_REPEAT_INPUT, 1)

    def get_schedule_rate_value(self):
        return self.driver.find_element_by_css_selector(self.SCHEDULE_RATE_CSS).get_attribute('value')

    def find_send_emails_toggle(self):
        return self.find_checkbox_by_label(self.SEND_EMAILS_LABEL)

    def find_disable_remember_me_toggle(self):
        return self.find_checkbox_by_label_with_single_quote(self.DISABLE_REMEMBER_ME)

    def find_getting_started_toggle(self):
        return self.find_checkbox_by_label(self.GETTING_STARTED_LABEL)

    def open_global_ssl_toggle(self, make_yes=True):
        toggle = self.find_checkbox_by_label(self.GLOBAL_SSL_LABEL)
        self.click_toggle_button(toggle, make_yes=make_yes)

    def set_global_ssl_settings(self, hostname: str, cert_data, private_data):
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
        self.click_button('ADVANCED SETTINGS', scroll_into_view_container=self.TABS_BODY_CSS)
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
        return self.find_checkbox_by_label(self.USE_SYSLOG_LABEL)

    def find_password_policy_toggle(self):
        return self.find_checkbox_by_label(self.ENFORCE_PASSWORD_POLICY)

    def fill_password_policy(self, password_length, min_lowercase, min_uppercase, min_numbers, min_special_chars):
        self.fill_text_field_by_element_id(self.MIN_PASSWORD_LENGTH_ID, password_length)
        self.fill_text_field_by_element_id(self.MIN_LOWERCASE_CHARS_ID, min_lowercase)
        self.fill_text_field_by_element_id(self.MIN_UPPERCASE_CHARS_ID, min_uppercase)
        self.fill_text_field_by_element_id(self.MIN_NUMBERS_CHARS_ID, min_numbers)
        self.fill_text_field_by_element_id(self.MIN_SPECIAL_CHARS_ID, min_special_chars)

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

    def fill_session_timeout(self, timeout):
        self.fill_text_field_by_element_id(self.TIMEOUT_ID, timeout)

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

    def wait_for_saved_successfully_toaster(self):
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
        self.wait_for_toaster('User permissions saved.')

    def find_allow_ldap_logins_toggle(self):
        return self.find_checkbox_by_label(self.LDAP_LOGINS_LABEL)

    def find_exact_search_toggle(self):
        return self.find_checkbox_by_label(self.EXACT_SEARCH_LABEL)

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

    def set_single_adapter_checkbox(self, make_yes=True):
        toggle = self.find_checkbox_by_label(self.SINGLE_ADAPTER_VIEW)
        self.click_toggle_button(toggle, make_yes=make_yes, scroll_to_toggle=True)

    def set_table_multi_line_checkbox(self, make_yes=True):
        toggle = self.find_checkbox_by_label(self.TABLE_MULTI_LINE_VIEW)
        self.click_toggle_button(toggle, make_yes=make_yes, scroll_to_toggle=True)

    def get_single_adapter_checkbox(self):
        return self.is_toggle_selected(self.find_checkbox_by_label(self.SINGLE_ADAPTER_VIEW))

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

    def save_and_wait_for_toaster(self):
        self.click_save_button()
        self.wait_for_saved_successfully_toaster()

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
        self.wait_for_toaster('Role saved.')

    def set_allow_saml_based_login(self, make_yes=True):
        toggle = self.find_checkbox_by_label(self.SAML_LOGINS_LABEL)
        self.click_toggle_button(toggle, make_yes=make_yes, window=TAB_BODY)

    def is_saml_login_enabled(self):
        toggle = self.find_checkbox_by_label(self.SAML_LOGINS_LABEL)
        return self.is_toggle_selected(toggle)

    def set_proxy_settings_enabled(self, make_yes=True):
        toggle = self.find_checkbox_by_label(self.USE_PROXY)
        self.click_toggle_button(toggle, make_yes=make_yes, scroll_to_toggle=False)

    def set_vault_settings_enabled(self, make_yes=True):
        self.wait_for_element_present_by_text(self.ENTERPRISE_PASSWORD_MGMT_TEXT)
        toggle = self.find_checkbox_by_label(self.USE_PASSWORD_MGR_VAULT)
        self.click_toggle_button(toggle, make_yes=make_yes, scroll_to_toggle=False)

    def set_gui_ssl_settings_enabled(self, make_yes=True):
        toggle = self.find_checkbox_by_label(self.USE_GUI_SSL)
        self.click_toggle_button(toggle, make_yes=make_yes, scroll_to_toggle=False)

    def set_correlation_schedule_settings_enabled(self, make_yes=True):
        toggle = self.find_checkbox_by_label(self.USE_CORRELATION_SCHEDULE)
        self.click_toggle_button(toggle, make_yes=make_yes, scroll_to_toggle=True)

    def set_amazon_settings_enabled(self, make_yes=True):
        toggle = self.find_checkbox_by_label(self.USE_AMAZON)
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
        return action_name in self.get_multiple_select_values()

    def get_locked_actions(self):
        return self.find_field_by_label('Actions Locked for Client').find_element_by_css_selector(
            '.v-select__selections')

    def set_locked_actions(self, action_name):
        locked_actions_el = self.get_locked_actions()
        locked_actions_el.click()
        self.driver.find_element_by_xpath(self.LOCKED_ACTION_OPTION_XPATH.format(action_name=action_name)).click()
        locked_actions_el.click()

    def fill_trial_expiration_by_remainder(self, days_remaining=None):
        element = self.find_elements_by_xpath(self.XPATH_BY_CLASS_NAME.format(name=self.DATEPICKER_CLASS_NAME))[0]
        try:
            self.clear_existing_date(context=element)
        except NoSuchElementException:
            pass
        if days_remaining is not None:
            self.fill_datepicker_date(datetime.now() + timedelta(days_remaining), context=element)
            self.close_datepicker()

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
                                      context=elements[1])
            self.close_datepicker()

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
        toggle = self.find_checkbox_by_label(label)
        self.click_toggle_button(toggle, make_yes=make_yes)

    def disable_custom_ca(self):
        label = self.driver.find_element_by_xpath(self.CA_CERTIFICATE_ENABLED).text
        toggle = self.find_checkbox_by_label(label)
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
        return self.driver.find_element_by_css_selector(self.CA_CERTS_FILES.format(file_index=ca_file_index + 1))

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
            self.CA_CERT_DELETE_BUTTON.format(file_index=ca_delete_index + 1))
        delete_button.click()

    @staticmethod
    def assert_ca_file_name_after_upload(cert_info: str):
        file_name, choose_file_label, x_label = cert_info.split('\n')
        assert file_name != 'No file chosen'
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
        return self.find_checkbox_by_label(self.SESSION_TIMEOUT_LABEL)

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
        return self.find_discovery_mode_dropdown().text

    def find_discovery_mode_dropdown(self):
        self.wait_for_element_present_by_css(self.DISCOVERY_SCHEDULE_MODE_DDL)
        return self.driver.find_element_by_css_selector(self.DISCOVERY_SCHEDULE_MODE_DDL)

    def get_discovery_mode_selected_item(self):
        return self.find_discovery_mode_dropdown().text

    def set_discovery_mode_dropdown_to_date(self):
        if self.get_discovery_mode_selected_item() != self.DISCOVERY_SCHEDULE_SCHEDULED_TEXT:
            self.select_option_without_search(self.DISCOVERY_SCHEDULE_MODE_DDL,
                                              self.SELECT_OPTION_CSS,
                                              self.DISCOVERY_SCHEDULE_SCHEDULED_TEXT)

    def set_discovery_mode_dropdown_to_interval(self):
        if self.get_discovery_mode_selected_item() != self.DISCOVERY_SCHEDULE_INTERVAL_TEXT:
            self.select_option_without_search(self.DISCOVERY_SCHEDULE_MODE_DDL,
                                              self.SELECT_OPTION_CSS,
                                              self.DISCOVERY_SCHEDULE_INTERVAL_TEXT)

    def set_discovery__to_interval_value(self, interval=0, negative_flow=False):
        self._set_discovery_schedule_settings(mode=self.DISCOVERY_SCHEDULE_INTERVAL_TEXT,
                                              time_value=interval,
                                              negative_flow=negative_flow)

    def set_discovery__to_time_of_day(self, time_of_day=0, negative_flow=False):
        self._set_discovery_schedule_settings(mode=self.DISCOVERY_SCHEDULE_SCHEDULED_TEXT,
                                              time_value=time_of_day,
                                              negative_flow=negative_flow)

    def set_date_format(self, date_format):
        self.select_option_without_search(self.DATE_FORMAT_CSS,
                                          self.SELECT_OPTION_CSS,
                                          date_format)

    def _set_discovery_schedule_settings(self, mode='', time_value=0, negative_flow=False):
        self.switch_to_page()

        if mode == self.DISCOVERY_SCHEDULE_INTERVAL_TEXT:
            self.set_discovery_mode_dropdown_to_interval()
            self.set_discovery_mode_to_rate_value(time_value)

        elif mode == self.DISCOVERY_SCHEDULE_SCHEDULED_TEXT:
            self.set_discovery_mode_dropdown_to_date()
            self.set_discovery_mode_to_date_value(time_value)

        else:
            raise RuntimeError('Invalid discovery schedule mode ')

        if negative_flow:
            # click to get error message display
            self.click_save_button()
            assert self.is_save_button_disabled()
        else:
            self.save_and_wait_for_toaster()

    def set_discovery_mode_to_rate_value(self, rate_hour_value):
        self.fill_schedule_rate(rate_hour_value)

    def set_discovery_mode_to_date_value(self, time_of_day_value):
        self.fill_schedule_date(time_of_day_value)

    def get_connection_label_required_value(self):
        self.switch_to_page()
        self.click_gui_settings()
        return self.driver.find_element_by_css_selector(self.CONNECTION_LABEL_REQUIRED_INPUT_CSS).is_selected()

    def toggle_connection_label_required(self):
        self.switch_to_page()
        self.click_gui_settings()
        self.driver.find_element_by_css_selector(self.CONNECTION_LABEL_REQUIRED_DIV_CSS).click()

    def close_role_panel(self):
        close_btn = self.wait_for_element_present_by_css(self.CSS_SELECTOR_CLOSE_PANEL_ACTION)
        close_btn.click()
        self.wait_for_role_panel_absent()

    def save_system_interval_schedule_settings(self, interval_value):
        session = requests.Session()
        cookies = self.driver.get_cookies()

        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])
        resp = session.get('https://127.0.0.1/api/csrf')
        csrf_token = resp.text
        resp.close()
        session.headers['X-CSRF-Token'] = csrf_token

        current_settings = self.get_current_schedule_settings(session)
        if current_settings is not None:
            current_settings['discovery_settings']['system_research_rate'] = interval_value
            current_settings['discovery_settings']['conditional'] = 'system_research_rate'

        result = session.post('https://127.0.0.1/api/settings/plugins/system_scheduler/SystemSchedulerService',
                              json=current_settings,
                              timeout=self.SETTINGS_SAVE_TIMEOUT)
        return result

    def open_discovery_mode_options(self):
        self.driver.find_element_by_css_selector(self.DISCOVERY_SCHEDULE_MODE_DDL).click()

    def find_discovery_mode_options(self):
        return self.driver.find_elements_by_css_selector(self.DISCOVERY_SCHEDULE_MODE_OPTIONS)

    def find_enterprise_password_mgmt_mode_dropdown(self):
        self.wait_for_element_present_by_css(self.ENTERPRISE_PASSWORD_MGMT_MODE_DDL)
        return self.driver.find_elements_by_tag_name(self.ENTERPRISE_PASSWORD_MGMT_MODE_DDL)[1]

    def get_enterprise_password_mgmt_settings_selected_item(self):
        return self.find_enterprise_password_mgmt_mode_dropdown().text

    def select_enterprise_password_mgmt_provider(self, vault_provider_text):
        if self.get_enterprise_password_mgmt_settings_selected_item() != vault_provider_text:
            self.select_option_without_search(self.ENTERPRISE_PASSWORD_MGMT_MODE_DDL,
                                              self.ENTERPRISE_PASSWORD_MGMT_MODE_DDL_OPTIONS,
                                              vault_provider_text)

    def select_thycotic_secret_server(self):
        self.select_enterprise_password_mgmt_provider(
            vault_provider_text=self.ENTERPRISE_PASSWORD_MGMT_THYCOTIC_SS_TEXT)

    def select_cyberark_secret_server(self):
        self.select_enterprise_password_mgmt_provider(
            vault_provider_text=self.ENTERPRISE_PASSWORD_MGMT_CYBERARK_VAULT_TEXT)

    def assert_server_error(self, error):
        assert self.wait_for_element_present_by_css(self.FOOTER_ERROR_CSS).text == error

    def wait_for_system_research_interval(self):
        self.wait_for_element_present_by_css(self.SCHEDULE_RATE_CSS)

    def get_current_schedule_settings(self, session):
        current_settings = session.get('https://127.0.0.1/api/settings/plugins/system_scheduler/SystemSchedulerService',
                                       timeout=self.SETTINGS_SAVE_TIMEOUT)
        return current_settings.json().get('config', None)

    def fill_thycotic_host(self, host):
        self.fill_text_field_by_element_id('host', host)

    def fill_thycotic_port(self, port):
        self.fill_text_field_by_element_id('port', port)

    def fill_thycotic_username(self, username):
        self.fill_text_field_by_element_id('username', username)

    def fill_thycotic_password(self, password):
        self.fill_text_field_by_element_id('password', password)

    def clear_enterprise_password_mgmt_settings(self):
        self.switch_to_page()
        self.click_global_settings()
        self.wait_for_element_present_by_text(self.ENTERPRISE_PASSWORD_MGMT_TEXT)
        toggle = self.find_checkbox_by_label(self.USE_PASSWORD_MGR_VAULT)
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

    def toggle_root_master(self, toggle_value):
        self.wait_for_element_present_by_text(self.USE_ROOT_MASTER)
        toggle = self.find_checkbox_by_label(self.USE_ROOT_MASTER)
        self.click_toggle_button(toggle, make_yes=toggle_value, scroll_to_toggle=False)

    def set_s3_integration_settings_enabled(self):
        toggle = self.find_checkbox_by_label(self.USE_S3_INTEGRATION)
        self.click_toggle_button(toggle, make_yes=True, scroll_to_toggle=False)

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

    def set_notify_on_adapters_fetch(self, enable=True):
        self.switch_to_page()
        self.click_global_settings()
        self.wait_for_spinner_to_end()
        toggle = self.find_notify_on_adapters_fetch_toggle()
        self.click_toggle_button(toggle, make_yes=enable, scroll_to_toggle=True)
        self.click_save_button()
        self.wait_for_saved_successfully_toaster()
