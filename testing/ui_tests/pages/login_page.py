from ui_tests.pages.page import Page


class LoginPage(Page):
    LOGIN_USERNAME_ID = 'user_name'
    LOGIN_PASSWORD_ID = 'password'
    LOGIN_DOMAIN_ID = 'domain'
    REMEMBER_ME_INPUT_CSS = '[for=remember_me]+div'
    LOGOUT_CSS = 'a[title="Logout"]'
    WRONG_USERNAME_OR_PASSWORD_MESSAGE = 'Wrong user name or password'
    LOGIN_WITH_LDAP_BUTTON_CLASS = 'x-button link'
    LOGIN_WITH_OKTA_BUTTON_CLASS = 'x-button link'
    OKTA_LOGIN_PASSWORD_ID = 'okta-signin-password'
    OKTA_LOGIN_USERNAME_ID = 'okta-signin-username'
    OKTA_URL = 'okta.axonius.local'
    OKTA_SUBMIT_BUTTON_ID = 'okta-signin-submit'

    @property
    def root_page_css(self):
        pass

    @property
    def url(self):
        pass

    def login(self, username, password, remember_me=False):
        self.fill_username(username)
        self.fill_password(password)
        if remember_me:
            self.click_remember_me()
        self.click_login_button()

    def fill_username(self, username):
        self.fill_text_field_by_element_id(self.LOGIN_USERNAME_ID, username)

    def fill_password(self, password):
        self.fill_text_field_by_element_id(self.LOGIN_PASSWORD_ID, password)

    def click_remember_me(self):
        toggle = self.driver.find_element_by_css_selector(self.REMEMBER_ME_INPUT_CSS)
        self.click_toggle_button(toggle,
                                 scroll_to_toggle=False)

    def click_login_button(self):
        self.click_button('Login')

    def logout(self):
        self.wait_for_element_present_by_css(self.LOGOUT_CSS)
        self.driver.find_element_by_css_selector(self.LOGOUT_CSS).click()

    def find_invalid_login_message(self):
        return self.find_element_by_text(self.WRONG_USERNAME_OR_PASSWORD_MESSAGE)

    def wait_for_invalid_login_message(self):
        return self.wait_for_element_present_by_text(self.WRONG_USERNAME_OR_PASSWORD_MESSAGE)

    def wait_for_login_page_to_load(self):
        self.wait_for_element_present_by_xpath(self.DISABLED_BUTTON_XPATH.format(button_text='Login'))

    def find_disabled_login_button(self):
        return self.driver.find_element_by_xpath(self.DISABLED_BUTTON_XPATH.format(button_text='Login'))

    def click_login_with_ldap(self):
        self.driver.find_element_by_id('ldap_login_link').click()

    def click_login_with_okta(self):
        self.driver.find_element_by_id('okta_login_link').click()

    def fill_okta_client_login_details(self, login_details):
        self.wait_for_element_present_by_id(self.OKTA_LOGIN_USERNAME_ID)
        self.fill_text_field_by_element_id(self.OKTA_LOGIN_USERNAME_ID, login_details['username'])
        self.fill_text_field_by_element_id(self.OKTA_LOGIN_PASSWORD_ID, login_details['password'])

    def fill_domain(self, domain):
        self.fill_text_field_by_element_id(self.LOGIN_DOMAIN_ID, domain)

    def fill_ldap_login_details(self, username, password, domain):
        user_elem = self.driver.find_elements_by_id(self.LOGIN_USERNAME_ID)[1]
        password_elem = self.driver.find_elements_by_id(self.LOGIN_PASSWORD_ID)[1]
        self.fill_text_by_element(user_elem, username)
        self.fill_text_by_element(password_elem, password)
        self.fill_domain(domain)

    def find_failed_ad_login_msg(self):
        return self.wait_for_element_present_by_text('Failed logging into AD')

    def find_failed_ad_login_msg_group(self, group_name):
        return self.wait_for_element_present_by_text(f'The provided user is not in the group ' + group_name)

    def switch_user(self, user_name, user_password):
        self.logout()
        self.wait_for_login_page_to_load()
        self.login(username=user_name, password=user_password)
