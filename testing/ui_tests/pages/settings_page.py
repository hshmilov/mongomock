import time
from datetime import datetime, timedelta

from selenium.common.exceptions import NoSuchElementException

from axonius.consts.gui_consts import PROXY_ERROR_MESSAGE
from services.axon_service import TimeoutException
from ui_tests.pages.page import PAGE_BODY, TAB_BODY, Page


class SettingsPage(Page):
    SCHEDULE_RATE_ID = 'system_research_rate'
    DEFAULT_SCHEDULE_RATE = '12'
    GLOBAL_SETTINGS_CSS = 'li#global-settings-tab'
    GUI_SETTINGS_CSS = 'li#gui-settings-tab'
    LIFECYCLE_SETTINGS_CSS = 'li#research-settings-tab'
    MANAGE_USERS_CSS = 'li#user-settings-tab'
    FEATURE_FLAGS_CSS = 'li#feature-flags-tab'
    ABOUT_CSS = 'li#about-settings-tab'
    SEND_EMAILS_LABEL = 'Send Emails'
    GETTING_STARTED_LABEL = 'Enable Getting Started with Axonius Checklist'
    GLOBAL_SSL_LABEL = 'Override Default SSL Settings'
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
    LDAP_LOGINS_LABEL = 'Allow LDAP Logins'
    OKTA_LOGINS_LABEL = 'Allow Okta Logins'
    SAML_LOGINS_LABEL = 'Allow SAML-Based Logins'
    TRIAL_MODE_FLAG_LABEL = 'Is trial mode'
    EMAIL_PORT_ID = 'smtpPort'
    EMAIL_HOST_ID = 'smtpHost'
    SYSLOG_HOST = 'syslogHost'
    SYSLOG_PORT = 'syslogPort'
    SYSLOG_SSL_CSS_DROPBOX = '[for=use_ssl]+div'
    SYSLOG_SSL_CSS_DROPBOX_OPTIONS = '[for=use_ssl]+div>.expand>div>.x-select-options>div'
    FRESH_SERVICE_DOMAIN = 'domain'
    FRESH_SERVICE_API_KEY = 'api_key'
    FRESH_SERVICE_ADMIN_EMAIL = 'admin_email'
    SAML_IDP = 'idp_name'
    HISTORY_GATHERED = 'Should history be gathered'
    DC_ADDRESS = 'dc_address'
    GROUP_CN = 'group_cn'
    SINGLE_ADAPTER_VIEW = 'Use Single Adapter View'
    TABLE_MULTI_LINE_VIEW = 'Use Table Multi Line View'
    ALLOW_GOOGLE_LOGINS = 'Allow Google logins'
    GOOGLE_CLIENT_ID_OLD = 'client_id'
    GOOGLE_CLIENT_ID = 'client'
    GOOGLE_EMAIL_OF_ADMIN = 'account_to_impersonate'
    READ_ONLY_PERMISSION = 'Read only'
    READ_WRITE_PERMISSION = 'Read and edit'
    RESTRICTED_PERMISSION = 'Restricted'
    SAVED_SUCCESSFULLY_TOASTER = 'Saved Successfully.'
    SAVED_SUCCESSFULLY_PERMISSIONS_TOASTER = 'User permissions saved.'
    BAD_PROXY_TOASTER = PROXY_ERROR_MESSAGE
    SELECT_ROLE_CSS = 'div.x-dropdown.x-select.select-role'
    SELECT_USER_ROLE_CSS = '.user-permissions .user-role .x-select'
    SELECT_OPTION_CSS = 'div.x-select-option'
    ADMIN_ROLE = 'Admin'
    READ_ONLY_ROLE = 'Read Only User'
    RESTRICTED_ROLE = 'Restricted User'
    USE_PROXY = 'Proxy Enabled'
    USE_CYBERARK_VAULT = 'Use CyberArk'
    VALUES_COUNT_PER_COLUMN_DROPDOWN_CSS = 'label[for="defaultColumnLimit"]~.x-dropdown.x-select'
    VALUES_COUNT_ENTITIES_PER_PAGE_CSS = 'label[for="defaultNumOfEntitiesPerPage"]~.x-dropdown.x-select'
    SAFEGUARD_REMOVE_BUTTON_TEXT = 'Remove Role'
    # sorry - but it's not my fault
    # https://axonius.atlassian.net/browse/AX-2991
    # those are the fully fledged css selectors for the elements
    CERT_ELEMENT_SELECTOR = '#app > div > .x-page > .body > div > div > div.x-tab.active.global-settings-tab' \
                            ' > .tab-settings > .x-form > .x-array-edit > div:nth-child(1) > div > div' \
                            ' > div:nth-child(4) > div > div > input[type="file"] '
    PRIVATE_ELEMENT_SELECTOR = '#app > div > .x-page > .body > div > div > div.x-tab.active.global-settings-tab' \
                               ' > .tab-settings > .x-form > .x-array-edit > div:nth-child(1) > div > div' \
                               ' > div:nth-child(5) > div > div > input[type="file"] '
    CERT_ELEMENT_FILENAME_SELECTOR = '#app > div > .x-page > .body > div > div > div.x-tab.active.global-settings-tab' \
                                     ' > .tab-settings > .x-form > .x-array-edit > div:nth-child(1) > div > div' \
                                     ' > div:nth-child(4) > div > div > div.file-name '
    PRIVATE_ELEMENT_FILENAME_SELECTOR = '#app > div > .x-page > .body > div > div > ' \
                                        'div.x-tab.active.global-settings-tab' \
                                        ' > .tab-settings > .x-form > .x-array-edit > div:nth-child(1) > div > div' \
                                        ' > div:nth-child(5) > div > div > div.file-name '

    LOCKED_ACTION_OPTION_XPATH = '//div[contains(@class, \'md-select-menu\')]//div[contains(@class, \'md-list-item\')]'\
                                 '//span[text()=\'{action_name}\']'

    TABS_BODY_CSS = '.x-tabs .body'

    CREATE_USER_BUTTON = 'Create User'
    UPDATE_USER_BUTTON = 'Update User'
    USER_DETAILS_SELECTOR = '.user-details-title'

    ROLE_PLACEHOLDER_CSS = '.user-role .x-select .placeholder'

    PERMISSION_LABEL_DEVICES = 'Devices'

    CA_CERTIFICATE_ENABLED = '//*[contains(text(),\'Certificate\')]'

    CA_ADD_CERT_BUTTON = '#ca_files ~ .x-button.light'
    CA_ADD_CERT_BUTTON_CSS = 'div.x-array-edit > div:nth-child(2) > div > div > div:nth-child(3) > div > div > button'

    CA_CERTS_FILES = 'div.x-array-edit > div:nth-child(2) > div > div >' \
                     ' div:nth-child(3) > div > div > div:nth-child({file_index})'

    CA_CERT_DELETE_BUTTON = f'{CA_CERTS_FILES} > button'

    @property
    def url(self):
        return f'{self.base_url}/settings'

    @property
    def root_page_css(self):
        return 'a#settings.item-link'

    def click_global_settings(self):
        self.driver.find_element_by_css_selector(self.GLOBAL_SETTINGS_CSS).click()

    def click_lifecycle_settings(self):
        self.driver.find_element_by_css_selector(self.LIFECYCLE_SETTINGS_CSS).click()

    def click_manage_users_settings(self):
        self.driver.find_element_by_css_selector(self.MANAGE_USERS_CSS).click()

    def click_new_user(self):
        self.click_button('+ New User')

    def click_edit_user(self, user_name):
        self.driver.find_element_by_id(user_name).click()

    def fill_new_user_details(self, username, password, first_name=None, last_name=None, role_name=None):
        self.fill_text_field_by_element_id('user_name', username)
        self.fill_text_field_by_element_id('password', password)
        if first_name:
            self.fill_text_field_by_element_id('first_name', first_name)
        if last_name:
            self.fill_text_field_by_element_id('last_name', last_name)
        if role_name:
            self.select_option_without_search('.x-users-roles .x-user-config .x-select',
                                              self.DROPDOWN_SELECTED_OPTION_CSS,
                                              role_name)

    def fill_edit_user_details(self, password=None, first_name=None, last_name=None):
        if password:
            self.fill_password_field(password)
        if first_name:
            self.fill_text_field_by_element_id('first_name', first_name)
        if last_name:
            self.fill_text_field_by_element_id('last_name', last_name)

    def fill_password_field(self, new_password):
        self.fill_text_field_by_element_id('password', new_password)

    def click_create_user(self):
        self.get_special_button(self.CREATE_USER_BUTTON).click()

    def click_update_user(self):
        self.get_special_button(self.UPDATE_USER_BUTTON).click()
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS)

    def find_disabled_create_user(self):
        return self.is_element_disabled(self.get_special_button(self.CREATE_USER_BUTTON))

    def find_password_input(self):
        return self.driver.find_element_by_id('password')

    def create_new_user(self, username, password, first_name=None, last_name=None, role_name=None):
        self.click_new_user()
        self.fill_new_user_details(username, password, first_name=first_name, last_name=last_name, role_name=role_name)
        self.click_create_user()
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS)

    def update_new_user(self, username, password=None, first_name=None, last_name=None):
        self.click_edit_user(username)
        self.fill_edit_user_details(password=password, first_name=first_name, last_name=last_name)
        self.click_update_user()
        self.wait_for_element_absent_by_css(self.MODAL_OVERLAY_CSS)

    def add_user_with_permission(self, username, password, first_name=None, last_name=None,
                                 permission_type: str = None, permission_level: str = None):
        self.switch_to_page()
        self.click_manage_users_settings()
        self.create_new_user(username, password, first_name, last_name)
        if permission_type and permission_level:
            self.select_permissions(permission_type, permission_level)
            self.click_save_manage_users_settings()
            self.wait_for_user_permissions_saved_toaster()

    def get_all_users_from_users_and_roles(self):
        return (x.text for x in self.driver.find_elements_by_css_selector(self.USER_DETAILS_SELECTOR))

    def click_gui_settings(self):
        self.driver.find_element_by_css_selector(self.GUI_SETTINGS_CSS).click()

    def click_feature_flags(self):
        self.driver.find_element_by_css_selector(self.FEATURE_FLAGS_CSS).click()

    def click_about(self):
        self.driver.find_element_by_css_selector(self.ABOUT_CSS).click()

    def get_save_button(self):
        return self.get_special_button('Save')

    def is_save_button_enabled(self):
        button = self.get_save_button()
        return button.get_attribute('class') != 'x-button disabled'

    def is_update_button_enabled(self):
        button = self.get_special_button(self.UPDATE_USER_BUTTON)
        return button.get_attribute('class') != 'x-button disabled'

    def click_save_button(self):
        self.get_save_button().click()

    def click_save_global_settings(self):
        self.click_generic_save_button('global-settings-save')

    def click_save_lifecycle_settings(self):
        self.click_generic_save_button('research-settings-save')

    def click_save_gui_settings(self):
        self.click_generic_save_button('gui-settings-save')

    def click_save_manage_users_settings(self):
        self.click_generic_save_button('user-settings-save')

    def click_generic_save_button(self, button_id):
        self.click_button_by_id(button_id, scroll_into_view_container=self.TABS_BODY_CSS)

    def fill_schedule_rate(self, text):
        self.fill_text_field_by_element_id(self.SCHEDULE_RATE_ID, text)

    def find_schedule_rate_error(self):
        self.find_element_by_text('\'Schedule Rate (hours)\' has an illegal value')

    def get_schedule_rate_value(self):
        return self.driver.find_element_by_id(self.SCHEDULE_RATE_ID).get_attribute('value')

    def find_send_emails_toggle(self):
        return self.find_checkbox_by_label(self.SEND_EMAILS_LABEL)

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
        self.click_button('ADVANCED SETTINGS', partial_class=True, scroll_into_view_container=self.TABS_BODY_CSS)
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

    def wait_for_user_created_toaster(self):
        self.wait_for_toaster('User created.')

    def wait_for_user_permissions_saved_toaster(self):
        self.wait_for_toaster('User permissions saved.')

    def find_allow_ldap_logins_toggle(self):
        return self.find_checkbox_by_label(self.LDAP_LOGINS_LABEL)

    def find_allow_okta_logins_toggle(self):
        return self.find_checkbox_by_label(self.OKTA_LOGINS_LABEL)

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

    def click_start_remote_access(self):
        self.click_button('Start', scroll_into_view_container=PAGE_BODY)

    def click_stop_remote_access(self):
        self.click_button('Stop', scroll_into_view_container=PAGE_BODY)

    def save_and_wait_for_toaster(self):
        self.click_save_button()
        self.wait_for_saved_successfully_toaster()

    def assert_screen_is_restricted(self):
        self.driver.find_element_by_css_selector('li.nav-item.disabled #settings')

    def select_permissions(self, label_text, permission):
        self.driver.find_element_by_xpath(self.DIV_BY_LABEL_TEMPLATE.format(label_text=label_text)). \
            find_element_by_css_selector('div.trigger-text'). \
            click()
        self.fill_text_field_by_css_selector('input.input-value', permission)
        self.driver.find_element_by_css_selector(self.SELECT_OPTION_CSS).click()

    def get_permissions_text(self, label_text):
        return self.driver.find_element_by_xpath(
            self.DIV_BY_LABEL_TEMPLATE.format(label_text=label_text)). \
            find_element_by_css_selector('div > div'). \
            text

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
        self.wait_for_toaster('User removed.')

    def remove_user(self):
        self.click_remove_user()
        self.click_confirm_remove_user()
        self.wait_for_user_removed_toaster()

    def click_roles_button(self):
        self.click_button_by_id('config-roles')

    def find_default_role(self):
        return self.driver.find_element_by_css_selector('div.roles-default')

    def assert_default_role_is_restricted(self):
        self.find_default_role().find_element_by_css_selector('div[title="Restricted User"]')

    def find_role_dropdown(self):
        return self.driver.find_element_by_css_selector(self.SELECT_ROLE_CSS)

    def assert_placeholder_is_new(self):
        assert self.find_role_dropdown().find_element_by_css_selector('div.placeholder').text == 'NEW'

    def select_role(self, role_text):
        self.select_option_without_search(self.SELECT_ROLE_CSS, self.SELECT_OPTION_CSS, role_text)

    def select_user_role(self, role_name):
        self.select_option_without_search(self.SELECT_USER_ROLE_CSS, self.SELECT_OPTION_CSS, role_name)

    def fill_role_name(self, text):
        self.fill_text_field_by_css_selector('input.name-role', text)

    def save_role(self):
        self.click_button_by_id('save-role-button')

    def remove_role(self, confirm=False):
        """
        the remove button is a safeguard button ( need to confirm )
        @param confirm: determine click on cancel or confirm
        @return: none
        """
        self.click_button_by_id('remove-role-button')
        if confirm:
            self.find_element_by_text(self.SAFEGUARD_REMOVE_BUTTON_TEXT).click()
        else:
            self.find_element_by_text('Cancel').click()

    def click_done(self):
        self.click_button('Done')

    def wait_for_role_saved_toaster(self):
        self.wait_for_toaster('Role saved.')

    def wait_for_role_removed_toaster(self):
        self.wait_for_toaster('Role removed.')

    def set_allow_saml_based_login(self, make_yes=True):
        toggle = self.find_checkbox_by_label(self.SAML_LOGINS_LABEL)
        self.click_toggle_button(toggle, make_yes=make_yes, window=TAB_BODY)

    def is_saml_login_enabled(self):
        toggle = self.find_checkbox_by_label(self.SAML_LOGINS_LABEL)
        return self.is_toggle_selected(toggle)

    def set_proxy_settings_enabled(self, make_yes=True):
        toggle = self.find_checkbox_by_label(self.USE_PROXY)
        self.click_toggle_button(toggle, make_yes=make_yes, scroll_to_toggle=False)

    def set_cyberark_vault_settings_enabled(self, make_yes=True):
        toggle = self.find_checkbox_by_label(self.USE_CYBERARK_VAULT)
        self.click_toggle_button(toggle, make_yes=make_yes, scroll_to_toggle=False)

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

    def get_locked_actions(self):
        return self.driver.find_element_by_css_selector('.md-select .md-input.md-select-value').get_attribute('value')

    def is_locked_action(self, action_name):
        return action_name in self.get_locked_actions()

    def set_locked_actions(self, action_name):
        self.find_field_by_label('Actions Locked for Client').click()
        self.driver.find_element_by_xpath(self.LOCKED_ACTION_OPTION_XPATH.format(action_name=action_name)).click()

    def fill_trial_expiration_by_remainder(self, days_remaining=None):
        try:
            self.clear_existing_date()
        except NoSuchElementException:
            pass
        if days_remaining is not None:
            self.fill_datepicker_date(datetime.now() + timedelta(days_remaining))
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
