from ui_tests.pages.page import Page


class LoginPage(Page):
    LOGIN_USERNAME_ID = 'user_name'
    LOGIN_PASSWORD_ID = 'password'
    LOGOUT_CSS = 'a[title="Logout"]'
    WRONG_USERNAME_OR_PASSWORD_MESSAGE = 'Wrong user name or password'
    DISABLED_BUTTON_XPATH = './/button[@class=\'x-btn disabled\' and .//text()=\'Login\']'

    @property
    def root_page_css(self):
        pass

    @property
    def url(self):
        pass

    def login(self, username, password):
        self.fill_username(username)
        self.fill_password(password)
        self.click_login_button()

    def fill_username(self, username):
        self.fill_text_field_by_element_id(self.LOGIN_USERNAME_ID, username)

    def fill_password(self, password):
        self.fill_text_field_by_element_id(self.LOGIN_PASSWORD_ID, password)

    def click_login_button(self):
        self.click_button('Login')

    def logout(self):
        self.driver.find_element_by_css_selector(self.LOGOUT_CSS).click()

    def find_invalid_login_message(self):
        return self.find_element_by_text(self.WRONG_USERNAME_OR_PASSWORD_MESSAGE)

    def wait_for_invalid_login_message(self):
        return self.wait_for_element_present_by_text(self.WRONG_USERNAME_OR_PASSWORD_MESSAGE)

    def wait_for_login_page_to_load(self):
        self.wait_for_element_present_by_xpath(self.DISABLED_BUTTON_XPATH)

    def find_disabled_login_button(self):
        return self.driver.find_element_by_xpath(self.DISABLED_BUTTON_XPATH)
