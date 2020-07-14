import pytest

from selenium.common.exceptions import NoSuchElementException

from ui_tests.pages.page import Page
from axonius.consts.system_consts import AXONIUS_DNS_SUFFIX
from test_credentials.test_gui_credentials import AXONIUS_USER


class LoginPage(Page):
    LOGIN_USERNAME_ID = 'user_name'
    LOGIN_PASSWORD_ID = 'password'
    LOGIN_DOMAIN_ID = 'domain'
    LOGIN_BUTTON = 'Login'
    REMEMBER_ME_INPUT_CSS = '[for=remember_me]+div'
    LOGOUT_CSS = 'a[title="Logout"]'
    WRONG_USERNAME_OR_PASSWORD_MESSAGE = 'Wrong user name or password'
    LOGIN_WITH_LDAP_BUTTON_CLASS = 'x-button link'
    LOGIN_WITH_OKTA_BUTTON_CLASS = 'x-button link'
    OKTA_LOGIN_PASSWORD_ID = 'okta-signin-password'
    OKTA_LOGIN_USERNAME_ID = 'okta-signin-username'
    OKTA_URL = f'okta.{AXONIUS_DNS_SUFFIX}'
    OKTA_SUBMIT_BUTTON_ID = 'okta-signin-submit'
    LOGIN_COMPONENT_CSS = '.x-login'
    NO_PERMISSION_MESSAGE = 'You are lacking some permissions for this request'

    @property
    def root_page_css(self):
        pass

    @property
    def url(self):
        pass

    def login(self, username, password, remember_me=False, wait_for_getting_started=True):
        self.fill_username(username)
        self.fill_password(password)
        if remember_me:
            self.click_remember_me()
        self.click_login_button()

        if wait_for_getting_started and self.test_base.should_getting_started_open():
            self.make_getting_started_disappear()
            print(f'Successfully marked getting started disappear')

    def fill_username(self, username):
        self.fill_text_field_by_element_id(self.LOGIN_USERNAME_ID, username)

    def fill_password(self, password):
        self.fill_text_field_by_element_id(self.LOGIN_PASSWORD_ID, password)

    def click_remember_me(self):
        toggle = self.driver.find_element_by_css_selector(self.REMEMBER_ME_INPUT_CSS)
        self.click_toggle_button(toggle, scroll_to_toggle=False)

    def click_login_button(self):
        return self.get_enabled_button(self.LOGIN_BUTTON).click()

    def logout(self):
        self.wait_for_element_present_by_css(self.LOGOUT_CSS)
        self.driver.find_element_by_css_selector(self.LOGOUT_CSS).click()
        self.wait_for_login_page_to_load()

    def logout_and_login_with_admin(self, wait_for_getting_started=True):
        self.logout()
        self.wait_for_login_page_to_load()
        self.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'],
                   wait_for_getting_started=wait_for_getting_started)

    def switch_user(self,
                    user_name,
                    user_password,
                    set_new_path=None,
                    wait_for_getting_started=True):
        self.logout()
        self.wait_for_login_page_to_load()
        if set_new_path:
            self.change_current_tab_url(self.current_url + set_new_path)
            self.wait_for_login_page_to_load()
        self.login(username=user_name,
                   password=user_password,
                   remember_me=False,
                   wait_for_getting_started=wait_for_getting_started)

    def find_invalid_login_message(self):
        return self.find_element_by_text(self.WRONG_USERNAME_OR_PASSWORD_MESSAGE)

    def wait_for_invalid_login_message(self):
        return self.wait_for_element_present_by_text(self.WRONG_USERNAME_OR_PASSWORD_MESSAGE)

    def wait_for_login_page_to_load(self):
        self.wait_for_element_present_by_xpath(self.DISABLED_BUTTON_XPATH.format(button_text=self.LOGIN_BUTTON))

    def wait_for_password_expired_warning(self):
        self.wait_for_element_present_by_css(self.ANT_CONFIRM_MODAL_TITLE_CSS)

    def find_disabled_login_button(self):
        return self.driver.find_element_by_xpath(self.DISABLED_BUTTON_XPATH.format(button_text=self.LOGIN_BUTTON))

    def click_login_with_ldap(self):
        self.driver.find_element_by_id('ldap_login_link').click()

    def click_login_with_okta(self):
        self.driver.find_element_by_id('okta_login_link').click()

    def click_login_with_saml(self):
        self.driver.find_element_by_id('saml_login_link').click()

    def login_with_saml_server(self, saml_server):
        self.wait_for_login_page_to_load()
        self.click_login_with_saml()
        # This method deals with a page served by the saml server docker container.
        # It is a page, and thus one might be tempted to create a Page class and file for it
        # I think that it is so tightly coupled to this container and code that it will cause
        # more confusion and won't reduce complexity.

        self.wait_for_element_present_by_text('A service has requested you to authenticate yourself.')
        self.fill_text_field_by_element_id('username', saml_server.test_user_name)
        self.fill_text_field_by_element_id('password', saml_server.test_user_password)
        self.find_element_by_text('Login').click()

    def login_with_okta_server(self, okta_login_details):
        self.click_login_with_saml()
        self.fill_okta_client_login_details(okta_login_details)
        self.driver.find_element_by_id(self.OKTA_SUBMIT_BUTTON_ID).click()
        self.wait_for_spinner_to_end()

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

    def find_remember_me_toggle(self):
        return self.driver.find_element_by_css_selector(self.REMEMBER_ME_INPUT_CSS)

    def find_failed_ad_login_msg_group(self, group_name):
        return self.wait_for_element_present_by_text(f'The provided user is not in the group ' + group_name)

    def make_getting_started_disappear(self):
        try:
            self.wait_for_element_present_by_css('.md-overlay')
        except Exception:
            # if overlay does not exist, most probably logged in user is not admin
            return
        self.click_getting_started_overlay()

    def assert_logged_in(self):
        with pytest.raises(NoSuchElementException):
            self.driver.find_element_by_css_selector(self.LOGIN_COMPONENT_CSS)

    def assert_not_logged_in(self):
        assert self.driver.find_element_by_css_selector(self.LOGIN_COMPONENT_CSS)

    def get_error_msg(self):
        return self.driver.find_element_by_css_selector('.x-login .form-error').text

    def assert_screen_url_is_restricted(self, screen):
        current_url = self.current_url
        screen.refresh()
        self.assert_not_logged_in()
        self.assert_login_permission_error_message()
        self.change_current_tab_url(current_url)

    def assert_login_permission_error_message(self):
        self.wait_for_login_page_to_load()
        assert self.get_error_msg() == self.NO_PERMISSION_MESSAGE

    def wait_for_no_permissions_message(self):
        return self.wait_for_element_present_by_text(self.NO_PERMISSION_MESSAGE)

    def wait_for_user_name(self):
        self.wait_for_element_present_by_id(self.LOGIN_USERNAME_ID)
