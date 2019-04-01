from ui_tests.pages.page import Page
from ui_tests.tests.ui_consts import SIGNUP_TEST_CREDS


class SignupPage(Page):
    COMPANY_NAME = 'companyName'
    CONTACT_EMAIL = 'contactEmail'
    NEW_PASSWORD = 'newPassword'
    CONFIRM_PASSWORD = 'confirmNewPassword'
    SIGNUP_COMPLETED_TOASTER = 'Sign up completed'
    PASSWORDS_DONT_MATCH_TOASTER = 'Passwords do not match'
    SIGNUP_FORM_CSS = '.x-signup-form'

    @property
    def url(self):
        return f'{self.base_url}'

    @property
    def root_page_css(self):
        return 'a[href="/"]'

    def fill_signup_with_defaults_and_save(self):
        self.fill_signup_and_save(company=SIGNUP_TEST_CREDS['company'],
                                  email=SIGNUP_TEST_CREDS['email'],
                                  passw=SIGNUP_TEST_CREDS['password'],
                                  confirm_passw=SIGNUP_TEST_CREDS['password'])

    def fill_signup_and_save(self, company, email, passw, confirm_passw):
        self.fill_text_field_by_element_id(self.COMPANY_NAME, company)
        self.fill_text_field_by_element_id(self.CONTACT_EMAIL, email)
        self.fill_text_field_by_element_id(self.NEW_PASSWORD, passw)
        self.fill_text_field_by_element_id(self.CONFIRM_PASSWORD, confirm_passw)
        self.click_save_button()

    def get_save_button(self):
        return self.get_special_button('Get Started')

    def is_signup_present(self):
        return self.get_save_button() is not None

    def click_save_button(self):
        self.get_save_button().click()

    def wait_for_signup_completed_toaster(self):
        self.wait_for_toaster(self.SIGNUP_COMPLETED_TOASTER)

    def wait_for_passwords_dont_match_toaster(self):
        self.wait_for_toaster(self.PASSWORDS_DONT_MATCH_TOASTER)

    def wait_for_signup_page_to_load(self):
        self.wait_for_element_present_by_css(self.SIGNUP_FORM_CSS)
