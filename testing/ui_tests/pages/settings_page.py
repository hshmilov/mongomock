from ui_tests.pages.page import Page


class SettingsPage(Page):
    CHANGE_ADMIN_PASSWORD_CSS = 'li#change-admin-password'
    CURRENT_PASSWORD_CSS = 'input#currentPassword'
    CURRENT_PASSWORD_ID = 'currentPassword'
    NEW_PASSWORD_ID = 'newPassword'
    CONFIRM_PASSWORD_ID = 'confirmNewPassword'
    PASSWORD_CHANGED_TOASTER = 'Password changed'
    GIVEN_PASSWORD_IS_WRONG_TOASTER = 'Given password is wrong'
    PASSWORDS_DONT_MATCH_TOASTER = 'Passwords don\'t match'
    SCHEDULE_RATE_ID = 'system_research_rate'
    DEFAULT_SCHEDULE_RATE = '12'
    GLOBAL_SETTINGS_CSS = 'li#global-settings-tab'
    SEND_EMAILS_CHECKBOX_CSS = 'div.x-checkbox-container'
    SEND_EMAILS_CHECKBOX_XPATH = '//div[child::label[text()=\'Send emails\']]/div[contains(@class, \'x-checkbox\')]'
    EMAIL_PORT_ID = 'smtpPort'
    EMAIL_HOST_ID = 'smtpHost'

    @property
    def url(self):
        return f'{self.base_url}/settings'

    @property
    def root_page_css(self):
        return 'a#settings.item-link'

    def click_change_admin_password(self):
        self.driver.find_element_by_css_selector(self.CHANGE_ADMIN_PASSWORD_CSS).click()

    def click_global_settings(self):
        self.driver.find_element_by_css_selector(self.GLOBAL_SETTINGS_CSS).click()

    def fill_current_password(self, password):
        self.fill_text_field_by_element_id(self.CURRENT_PASSWORD_ID, password)

    def fill_new_password(self, password):
        self.fill_text_field_by_element_id(self.NEW_PASSWORD_ID, password)

    def fill_confirm_password(self, password):
        self.fill_text_field_by_element_id(self.CONFIRM_PASSWORD_ID, password)

    def get_save_button(self):
        return self.get_special_button('Save')

    def is_save_button_enabled(self):
        button = self.get_save_button()
        return button.get_attribute('class') != 'x-btn disabled'

    def click_save_button(self):
        self.get_save_button().click()

    def wait_for_password_changed_toaster(self):
        self.wait_for_toaster(self.PASSWORD_CHANGED_TOASTER)

    def wait_for_given_password_is_wrong_toaster(self):
        self.wait_for_toaster(self.GIVEN_PASSWORD_IS_WRONG_TOASTER)

    def wait_for_passwords_dont_match_toaster(self):
        self.wait_for_toaster(self.PASSWORDS_DONT_MATCH_TOASTER)

    def fill_schedule_rate(self, text):
        self.fill_text_field_by_element_id(self.SCHEDULE_RATE_ID, text)

    def find_schedule_rate_error(self):
        self.find_element_by_text('\'Schedule Rate (hours)\' has an illegal value')

    def get_schedule_rate_value(self):
        return self.driver.find_element_by_id(self.SCHEDULE_RATE_ID).get_attribute('value')

    def find_send_emails_toggle(self):
        return self.driver.find_element_by_xpath(self.SEND_EMAILS_CHECKBOX_XPATH)

    def set_send_emails_toggle(self):
        toggle = self.find_send_emails_toggle()
        self.click_toggle_button(toggle, make_yes=True, scroll_to_toggle=True)

    def fill_email_port(self, port):
        self.fill_text_field_by_element_id(self.EMAIL_PORT_ID, port)

    def fill_email_host(self, host):
        self.fill_text_field_by_element_id(self.EMAIL_HOST_ID, host)

    def find_email_port_error(self):
        return self.find_element_by_text('\'Port\' has an illegal value')

    def get_email_port(self):
        return self.driver.find_element_by_id(self.EMAIL_PORT_ID).get_attribute('value')

    def get_email_host(self):
        return self.driver.find_element_by_id(self.EMAIL_HOST_ID).get_attribute('value')
