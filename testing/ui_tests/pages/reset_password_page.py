from ui_tests.pages.page import Page


class ResetPasswordPage(Page):
    NEW_PASSWORD_ID = 'newPassword'
    CONFIRM_NEW_PASSWORD_ID = 'confirmNewPassword'
    SET_PASSWORD_BUTTON = 'Set Password'
    RESET_PASSWORD_TOASTER_TEXT = 'Password reset successful'

    @property
    def root_page_css(self):
        pass

    @property
    def url(self):
        pass

    def fill_new_password(self, password):
        self.fill_text_field_by_element_id(self.NEW_PASSWORD_ID, password)

    def fill_confirm_new_password(self, password):
        self.fill_text_field_by_element_id(self.CONFIRM_NEW_PASSWORD_ID, password)

    def click_set_password_button(self):
        return self.get_enabled_button(self.SET_PASSWORD_BUTTON).click()

    def set_new_password(self, password):
        self.fill_new_password(password)
        self.fill_confirm_new_password(password)
        self.click_set_password_button()

    def wait_for_expired_msg(self):
        self.wait_for_element_present_by_css('.expired-text')

    def wait_for_reset_password_page_to_load(self):
        self.wait_for_element_present_by_xpath(self.DISABLED_BUTTON_XPATH.format(button_text=self.SET_PASSWORD_BUTTON))

    def reset_password_via_link(self, link, password):
        self.driver.get(link)
        self.wait_for_reset_password_page_to_load()
        self.set_new_password(password)
        self.wait_for_toaster(self.RESET_PASSWORD_TOASTER_TEXT)
