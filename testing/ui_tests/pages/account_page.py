from typing import Callable

from ui_tests.pages.entities_page import EntitiesPage


class AccountPage(EntitiesPage):
    ACCOUNT_SET_SECRET_KEY_INVISIBLE_ICON_CSS = '.apikey-account-tab .hide-key-icon'
    ACCOUNT_SET_SECRET_KEY_VISIBLE_ICON_CSS = '.apikey-account-tab .show-key-icon'
    ACCOUNT_COPY_TO_CLIPBOARD_ICON_CSS = '.apikey-account-tab .copy-to-clipboard-icon'
    ACCOUNT_GET_SECRET_KEY_MASKED_CSS = '.apikey-account-tab input.invisible.secret-key'
    ACCOUNT_GET_SECRET_KEY_VISIBLE_CSS = '.apikey-account-tab input.visible.secret-key'

    CHANGE_ADMIN_PASSWORD_CSS = 'li#password-account-tab'
    CURRENT_PASSWORD_CSS = 'input#currentPassword'
    CURRENT_PASSWORD_ID = 'currentPassword'
    NEW_PASSWORD_ID = 'newPassword'
    CONFIRM_PASSWORD_ID = 'confirmNewPassword'
    PASSWORD_CHANGED_TOASTER = 'Password changed'
    GIVEN_PASSWORD_IS_WRONG_TOASTER = 'Given password is wrong'
    PASSWORDS_DONT_MATCH_TOASTER = 'Passwords do not match'
    ERROR_TEXT_CSS = '.error-text'

    @property
    def root_page_css(self):
        return 'a[title="My Account"]'

    @property
    def url(self):
        return f'{self.base_url}/account'

    def get_api_key_and_secret(self):
        grid_div = self.driver.find_element_by_xpath(self.DIV_BY_LABEL_TEMPLATE.format(label_text='API key:'))
        elems = grid_div.find_elements_by_css_selector('div')
        return {'key': elems[0].text, 'secret': self.get_visible_secret_key_field_value()}

    def reset_api_key_and_secret(self):
        self.click_button('Reset Key', should_scroll_into_view=False)
        self.wait_for_element_present_by_id('approve-reset-api-key')
        self.click_button_by_id('approve-reset-api-key', should_scroll_into_view=False)
        self.wait_for_toaster('a new secret key has been generated, the old one is no longer valid')

    def is_reset_key_displayed(self):
        return not self.is_button_absent('Reset Key')

    def is_key_secret_displayed(self):
        return self.driver.find_element_by_css_selector(self.ACCOUNT_GET_SECRET_KEY_VISIBLE_CSS).is_displayed()

    def is_key_mask_displayed(self):
        return self.driver.find_element_by_css_selector(self.ACCOUNT_GET_SECRET_KEY_MASKED_CSS).is_displayed()

    def is_set_secret_key_visisble_icon(self):
        return self.driver.find_element_by_css_selector(self.ACCOUNT_SET_SECRET_KEY_VISIBLE_ICON_CSS).is_displayed()

    def is_set_secret_key_invisisble_icon(self):
        return self.driver.find_element_by_css_selector(self.ACCOUNT_SET_SECRET_KEY_INVISIBLE_ICON_CSS).is_displayed()

    def click_show_secret_api_key_button(self):
        self.driver.find_element_by_css_selector(self.ACCOUNT_SET_SECRET_KEY_VISIBLE_ICON_CSS).click()

    def click_hide_secret_api_key_button(self):
        self.driver.find_element_by_css_selector(self.ACCOUNT_SET_SECRET_KEY_INVISIBLE_ICON_CSS).click()

    def click_copy_to_clipboard(self):
        self.driver.find_element_by_css_selector(self.ACCOUNT_COPY_TO_CLIPBOARD_ICON_CSS).click()

    def get_visible_secret_key_field_value(self):
        return self.driver.find_element_by_css_selector(self.ACCOUNT_GET_SECRET_KEY_VISIBLE_CSS).get_attribute('value')

    def get_masked_secret_key_field_value(self):
        return self.driver.find_element_by_css_selector(self.ACCOUNT_GET_SECRET_KEY_MASKED_CSS).get_attribute('value')

    def click_change_admin_password(self):
        self.driver.find_element_by_css_selector(self.CHANGE_ADMIN_PASSWORD_CSS).click()

    def fill_current_password(self, password):
        self.fill_text_field_by_element_id(self.CURRENT_PASSWORD_ID, password)

    def fill_new_password(self, password):
        self.fill_text_field_by_element_id(self.NEW_PASSWORD_ID, password)

    def get_user_dialog_error(self):
        return self.driver.find_element_by_css_selector(self.ERROR_TEXT_CSS).text

    def fill_confirm_password(self, password):
        self.fill_text_field_by_element_id(self.CONFIRM_PASSWORD_ID, password)

    def click_save_button(self):
        self.get_save_button().click()

    def wait_for_password_changed_toaster(self):
        self.wait_for_toaster(self.PASSWORD_CHANGED_TOASTER)

    def wait_for_given_password_is_wrong_toaster(self):
        self.wait_for_toaster(self.GIVEN_PASSWORD_IS_WRONG_TOASTER)

    def wait_for_passwords_dont_match_toaster(self):
        self.wait_for_toaster(self.PASSWORDS_DONT_MATCH_TOASTER)

    def change_password(self, current, new1, new2, wait_for: Callable = None):
        self.click_change_admin_password()
        self.fill_current_password(current)
        self.fill_new_password(new1)
        self.fill_confirm_password(new2)
        self.click_save_button()
        if wait_for:
            wait_for()
