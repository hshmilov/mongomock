from ui_tests.pages.page import Page, X_BODY


class SettingsPage(Page):
    SCHEDULE_RATE_ID = 'system_research_rate'
    DEFAULT_SCHEDULE_RATE = '12'
    GLOBAL_SETTINGS_CSS = 'li#global-settings-tab'
    GUI_SETTINGS_CSS = 'li#gui-settings-tab'
    LIFECYCLE_SETTINGS_CSS = 'li#research-settings-tab'
    MANAGE_USERS_CSS = 'li#user-settings-tab'
    ABOUT_CSS = 'li#about-settings-tab'
    SEND_EMAILS_CHECKBOX_CSS = 'div.x-checkbox-container'
    SEND_EMAILS_LABEL = 'Send emails'
    REMOTE_SUPPORT_LABEL = 'Remote Support - Warning: turning off this feature prevents Axonius from' \
                           '                             updating the system and can lead' \
                           ' to slower issue resolution time.' \
                           '                             Note: anonymized analytics must be enabled for remote support'
    USE_SYSLOG_LABEL = 'Use syslog'
    LDAP_LOGINS_LABEL = 'Allow LDAP logins'
    OKTA_LOGINS_LABEL = 'Allow Okta logins'
    EMAIL_PORT_ID = 'smtpPort'
    EMAIL_HOST_ID = 'smtpHost'
    SYSLOG_HOST = 'syslogHost'
    SYSLOG_PORT = 'syslogPort'
    USE_FRESH_SERVICE = 'Use FreshService'
    FRESH_SERVICE_DOMAIN = 'domain'
    FRESH_SERVICE_API_KEY = 'api_key'
    FRESH_SERVICE_ADMIN_EMAIL = 'admin_email'
    USE_EXECUTION = 'Execution Enabled'
    HISTORY_GATHERED = 'Should history be gathered'
    DC_ADDRESS = 'dc_address'
    SINGLE_ADAPTER_VIEW = 'Use Single Adapter View'
    ALLOW_GOOGLE_LOGINS = 'Allow Google logins'
    GOOGLE_CLIENT_ID = 'Google client id'
    GOOGLE_EMAIL_OF_ADMIN = 'Email of an admin account to impersonate'
    READ_ONLY_PERMISSION = 'Read only'
    RESTRICTED_PERMISSION = 'Restricted'

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

    def fill_new_user_details(self, username, password, first_name=None, last_name=None):
        self.fill_text_field_by_element_id('user_name', username)
        self.fill_text_field_by_element_id('password', password)
        if first_name:
            self.fill_text_field_by_element_id('first_name', first_name)
        if last_name:
            self.fill_text_field_by_element_id('last_name', last_name)

    def click_create_user(self):
        self.click_button('Create User')

    def create_new_user(self, username, password, first_name=None, last_name=None):
        self.click_new_user()
        self.fill_new_user_details(username, password, first_name=first_name, last_name=last_name)
        self.click_create_user()

    def get_all_users_from_users_and_roles(self):
        return (x.text for x in self.driver.find_elements_by_css_selector('.user-details-title'))

    def click_gui_settings(self):
        self.driver.find_element_by_css_selector(self.GUI_SETTINGS_CSS).click()

    def click_about(self):
        self.driver.find_element_by_css_selector(self.ABOUT_CSS).click()

    def get_save_button(self):
        return self.get_special_button('Save')

    def is_save_button_enabled(self):
        button = self.get_save_button()
        return button.get_attribute('class') != 'x-btn disabled'

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
        self.click_button_by_id(button_id, scroll_into_view_container=X_BODY)

    def fill_schedule_rate(self, text):
        self.fill_text_field_by_element_id(self.SCHEDULE_RATE_ID, text)

    def find_schedule_rate_error(self):
        self.find_element_by_text('\'Schedule Rate (hours)\' has an illegal value')

    def get_schedule_rate_value(self):
        return self.driver.find_element_by_id(self.SCHEDULE_RATE_ID).get_attribute('value')

    def find_send_emails_toggle(self):
        return self.find_checkbox_by_label(self.SEND_EMAILS_LABEL)

    def find_remote_support_toggle(self):
        return self.find_checkbox_by_label(self.REMOTE_SUPPORT_LABEL)

    def find_syslog_toggle(self):
        return self.find_checkbox_by_label(self.USE_SYSLOG_LABEL)

    def find_fresh_service_toggle(self):
        return self.find_checkbox_by_label(self.USE_FRESH_SERVICE)

    def find_execution_toggle(self):
        return self.find_checkbox_by_label(self.USE_EXECUTION)

    def find_should_history_be_gathered_toggle(self):
        return self.find_checkbox_by_label(self.HISTORY_GATHERED)

    def set_send_emails_toggle(self):
        toggle = self.find_send_emails_toggle()
        self.click_toggle_button(toggle, make_yes=True, scroll_to_toggle=True)

    def set_remote_support_toggle(self, make_yes):
        toggle = self.find_remote_support_toggle()
        self.click_toggle_button(toggle, make_yes=make_yes, scroll_to_toggle=True)

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

    def find_email_connection_failure_toaster(self, host):
        return self.find_toaster(f'Could not connect to mail server "{host}"')

    def find_saved_successfully_toaster(self):
        return self.find_toaster('Saved Successfully.')

    def find_allow_ldap_logins_toggle(self):
        return self.find_checkbox_by_label(self.LDAP_LOGINS_LABEL)

    def find_allow_okta_logins_toggle(self):
        return self.find_checkbox_by_label(self.OKTA_LOGINS_LABEL)

    def fill_dc_address(self, dc_address):
        self.fill_text_field_by_element_id(self.DC_ADDRESS, dc_address)

    def fill_okta_login_details(self, client_id, client_secret, url, gui_url):
        self.fill_text_field_by_element_id('client_id', client_id)
        self.fill_text_field_by_element_id('client_secret', client_secret)
        self.fill_text_field_by_element_id('url', url)
        self.fill_text_field_by_element_id('gui_url', gui_url)

    def get_dc_address(self):
        return self.driver.find_element_by_id(self.DC_ADDRESS).get_attribute('value')

    def get_okta_login_details(self):
        return {
            'client_id': self.driver.find_element_by_id('client_id').get_attribute('value'),
            'client_secret': self.driver.find_element_by_id('client_secret').get_attribute('value'),
            'url': self.driver.find_element_by_id('url').get_attribute('value'),
            'gui_url': self.driver.find_element_by_id('gui_url').get_attribute('value')
        }

    def set_single_adapter_checkbox(self, make_yes=True):
        toggle = self.find_checkbox_by_label(self.SINGLE_ADAPTER_VIEW)
        self.click_toggle_button(toggle, make_yes=make_yes, scroll_to_toggle=True)

    def get_single_adapter_checkbox(self):
        return self.is_toggle_selected(self.find_checkbox_by_label(self.SINGLE_ADAPTER_VIEW))

    def set_google_clients_login(self, make_yes=True):
        toggle = self.find_checkbox_by_label(self.ALLOW_GOOGLE_LOGINS)
        self.click_toggle_button(toggle, make_yes=make_yes, scroll_to_toggle=True)

    def get_google_clients_login(self):
        return self.is_toggle_selected(self.find_checkbox_by_label(self.ALLOW_GOOGLE_LOGINS))

    def set_google_client_id(self, text):
        self.fill_text_field_by_element_id(self.GOOGLE_CLIENT_ID, text)

    def get_google_client_id(self):
        return self.driver.find_element_by_id(self.GOOGLE_CLIENT_ID).get_attribute('value')

    def set_google_email_account(self, text):
        self.fill_text_field_by_element_id(self.GOOGLE_EMAIL_OF_ADMIN, text)

    def get_google_email_account(self):
        return self.driver.find_element_by_id(self.GOOGLE_EMAIL_OF_ADMIN).get_attribute('value')

    def find_checkbox_by_label(self, text):
        return self.driver.find_element_by_xpath(self.CHECKBOX_XPATH_TEMPLATE.format(label_text=text))

    def click_start_remote_access(self):
        self.click_button('Start', button_class='x-btn right', scroll_into_view_container=X_BODY)

    def save_and_wait_for_toaster(self):
        self.click_save_button()
        self.wait_for_toaster('Saved Successfully.')

    def assert_screen_is_restricted(self):
        self.driver.find_element_by_css_selector('li.nav-item.disabled #settings')

    def select_permissions(self, label_text, permission):
        self.driver.find_element_by_xpath(
            f'//div[child::label[text()=\'{label_text}\']]').find_element_by_css_selector('div.trigger-text').click()
        self.fill_text_field_by_css_selector('input.input-value', permission)
        self.driver.find_element_by_css_selector('div.x-select-option').click()

    @staticmethod
    def get_permission_labels():
        labels = ('Adapters Permissions',
                  'Devices Permissions',
                  'Users Permissions',
                  'Alerts Permissions',
                  'Reports Permissions',
                  'Settings Permissions')
        return labels
