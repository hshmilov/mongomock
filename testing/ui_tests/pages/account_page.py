from ui_tests.pages.entities_page import EntitiesPage


class AccountPage(EntitiesPage):
    ACCOUNT_SET_SECRET_KEY_INVISIBLE_ICON_CSS = '.apikey-account-tab .md-icon.hide-key-icon'
    ACCOUNT_SET_SECRET_KEY_VISIBLE_ICON_CSS = '.apikey-account-tab .md-icon.show-key-icon'
    ACCOUNT_COPY_TO_CLIPBOARD_ICON_CSS = '.apikey-account-tab .md-icon.copy-to-clipboard-icon'
    ACCOUNT_GET_SECRET_KEY_MASKED_CSS = '.apikey-account-tab input.invisible.secret-key'
    ACCOUNT_GET_SECRET_KEY_VISIBLE_CSS = '.apikey-account-tab input.visible.secret-key'

    @property
    def root_page_css(self):
        return 'a[title="My Account"]'

    @property
    def url(self):
        return f'{self.base_url}/account'

    def get_api_key_and_secret(self):
        grid_div = self.driver.find_element_by_xpath(self.DIV_BY_LABEL_TEMPLATE.format(label_text='API Key:'))
        elems = grid_div.find_elements_by_css_selector('div')
        return {'key': elems[0].text, 'secret': self.get_visible_secret_key_field_value()}

    def reset_api_key_and_secret(self):
        self.click_button('Reset Key', should_scroll_into_view=False)
        self.wait_for_element_present_by_id('approve-reset-api-key')
        self.click_button_by_id('approve-reset-api-key', should_scroll_into_view=False)
        self.wait_for_toaster('a new secret key has been generated, the old one is no longer valid')

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
