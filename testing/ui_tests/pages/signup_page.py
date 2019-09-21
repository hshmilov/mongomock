from axonius.consts.gui_consts import (Signup, SIGNUP_TEST_CREDS)
from ui_tests.pages.page import Page


class SignupPage(Page):
    COMPANY_NAME = 'companyName'
    CONTACT_EMAIL = 'contactEmail'
    NEW_PASSWORD = 'newPassword'
    CONFIRM_PASSWORD = 'confirmNewPassword'
    SIGNUP_COMPLETED_TOASTER = 'Sign up completed'
    PASSWORDS_DONT_MATCH_MESSAGE = 'Passwords do not match'
    SIGNUP_FORM_CSS = '.x-signup-form'
    BASE_TITLE = '\'{title}\' has an illegal value'
    COMPANY_NAME_TITLE = 'Your Organization'
    NEW_PASSWORD_TITLE = 'Set Password'
    CONFIRM_PASSWORD_TITLE = 'Confirm Password'
    CONTACT_EMAIL_ERROR_MSG = 'Please enter a valid email address'
    NONE_ERROR_MSG = ' '

    FIELDS_ERROR_MESSAGES = {
        COMPANY_NAME: BASE_TITLE.format(title=COMPANY_NAME_TITLE),
        CONTACT_EMAIL: CONTACT_EMAIL_ERROR_MSG,
        NEW_PASSWORD: BASE_TITLE.format(title=NEW_PASSWORD_TITLE),
        CONFIRM_PASSWORD: BASE_TITLE.format(title=CONFIRM_PASSWORD_TITLE),
    }

    @property
    def url(self):
        return f'{self.base_url}'

    @property
    def root_page_css(self):
        return 'a[href="/"]'

    def fill_signup_with_defaults_and_save(self):
        self.fill_signup_and_save(company=SIGNUP_TEST_CREDS[Signup.CompanyField],
                                  email=SIGNUP_TEST_CREDS[Signup.ContactEmailField],
                                  passw=SIGNUP_TEST_CREDS[Signup.NewPassword],
                                  confirm_passw=SIGNUP_TEST_CREDS[Signup.NewPassword])

    def fill_signup_and_save(self, company, email, passw, confirm_passw):
        self.fill_signup(company, email, passw, confirm_passw)
        self.save_form()

    def fill_signup(self, company, email, passw, confirm_passw):
        self.fill_text_field_by_element_id(self.COMPANY_NAME, company)
        self.fill_text_field_by_element_id(self.CONTACT_EMAIL, email)
        self.fill_text_field_by_element_id(self.NEW_PASSWORD, passw)
        self.fill_text_field_by_element_id(self.CONFIRM_PASSWORD, confirm_passw)

    def save_form(self):
        self.click_save_button()

    def get_error_msg(self):
        return self.driver.find_element_by_css_selector('.x-signup-form .error').text

    def get_save_button(self):
        return self.get_special_button('Get Started')

    def is_signup_present(self):
        return self.get_save_button() is not None

    def click_save_button(self):
        self.get_save_button().click()

    def wait_for_signup_completed_toaster(self):
        self.wait_for_toaster(self.SIGNUP_COMPLETED_TOASTER)

    def wait_for_passwords_dont_match_error(self):
        self.wait_for_element_present_by_text(self.PASSWORDS_DONT_MATCH_MESSAGE)

    def wait_for_signup_page_to_load(self):
        self.wait_for_element_present_by_css(self.SIGNUP_FORM_CSS)
