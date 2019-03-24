from ui_tests.pages.page import Page


class MyAccountPage(Page):
    CHANGE_ADMIN_PASSWORD_CSS = 'li#password-account-tab'
    CURRENT_PASSWORD_CSS = 'input#currentPassword'
    CURRENT_PASSWORD_ID = 'currentPassword'
    NEW_PASSWORD_ID = 'newPassword'
    CONFIRM_PASSWORD_ID = 'confirmNewPassword'
    PASSWORD_CHANGED_TOASTER = 'Password changed'
    GIVEN_PASSWORD_IS_WRONG_TOASTER = 'Given password is wrong'
    PASSWORDS_DONT_MATCH_TOASTER = 'Passwords do not match'

    @property
    def url(self):
        return f'{self.base_url}/my_account'

    @property
    def root_page_css(self):
        return 'a[href="/account"]'

    def click_change_admin_password(self):
        self.driver.find_element_by_css_selector(self.CHANGE_ADMIN_PASSWORD_CSS).click()

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
        return button.get_attribute('class') != 'x-button disabled'

    def click_save_button(self):
        self.get_save_button().click()

    def wait_for_password_changed_toaster(self):
        self.wait_for_toaster(self.PASSWORD_CHANGED_TOASTER)

    def wait_for_given_password_is_wrong_toaster(self):
        self.wait_for_toaster(self.GIVEN_PASSWORD_IS_WRONG_TOASTER)

    def wait_for_passwords_dont_match_toaster(self):
        self.wait_for_toaster(self.PASSWORDS_DONT_MATCH_TOASTER)

    def change_password(self, current, new1, new2, wait_for=None):
        self.click_change_admin_password()
        self.fill_current_password(current)
        self.fill_new_password(new1)
        self.fill_confirm_password(new2)
        self.click_save_button()
        if wait_for:
            wait_for()
