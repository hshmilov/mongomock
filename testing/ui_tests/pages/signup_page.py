from ui_tests.pages.page import Page


class SignupPage(Page):
    COMPANY_NAME = 'companyName'
    CONTACT_EMAIL = 'contactEmail'
    NEW_PASSWORD = 'newPassword'
    CONFIRM_PASSWORD = 'confirmNewPassword'
    SIGNUP_COMPLETED_TOASTER = 'Sign up completed'
    PASSWORDS_DONT_MATCH_TOASTER = 'Passwords do not match'
    SAVE_BUTTON_ID = 'signup-save'

    @property
    def url(self):
        return f'{self.base_url}'

    @property
    def root_page_css(self):
        return 'a[href="/"]'

    def fill_signup_and_save(self, company, email, passw, confirm_passw):
        self.fill_text_field_by_element_id(self.COMPANY_NAME, company)
        self.fill_text_field_by_element_id(self.CONTACT_EMAIL, email)
        self.fill_text_field_by_element_id(self.NEW_PASSWORD, passw)
        self.fill_text_field_by_element_id(self.CONFIRM_PASSWORD, confirm_passw)
        self.click_save_button()

    def get_save_button(self):
        return self.get_special_button('Save')

    def is_signup_present(self):
        return self.get_save_button() is not None

    def click_save_button(self):
        self.get_save_button().click()

    def wait_for_signup_completed_toaster(self):
        self.wait_for_toaster(self.SIGNUP_COMPLETED_TOASTER)

    def wait_for_passwords_dont_match_toaster(self):
        self.wait_for_toaster(self.PASSWORDS_DONT_MATCH_TOASTER)

    def wait_for_signup_page_to_load(self):
        self.wait_for_element_present_by_id(self.SAVE_BUTTON_ID)
