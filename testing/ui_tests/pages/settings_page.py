from ui_tests.pages.page import Page


class SettingsPage(Page):
    SCHEDULE_RATE_ID = 'system_research_rate'
    DEFAULT_SCHEDULE_RATE = '12'
    GLOBAL_SETTINGS_CSS = 'li#global-settings-tab'
    GUI_SETTINGS_CSS = 'li#gui-settings-tab'
    LIFECYCLE_SETTINGS_CSS = 'li#research-settings-tab'
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

    def find_exection_toggle(self):
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
        self.fill_text_field_by_element_id('dc_address', dc_address)

    def fill_okta_login_details(self, client_id, client_secret, url, gui_url):
        self.fill_text_field_by_element_id('client_id', client_id)
        self.fill_text_field_by_element_id('client_secret', client_secret)
        self.fill_text_field_by_element_id('url', url)
        self.fill_text_field_by_element_id('gui_url', gui_url)

    def find_checkbox_by_label(self, text):
        return self.driver.find_element_by_xpath(self.CHECKBOX_XPATH_TEMPLATE.format(label_text=text))

    def save_and_wait_for_toaster(self):
        self.click_save_button()
        self.wait_for_toaster('Saved Successfully.')
