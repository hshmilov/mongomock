from ui_tests.pages.entities_page import EntitiesPage


class AccountPage(EntitiesPage):
    @property
    def root_page_css(self):
        return 'a[title="My Account"]'

    @property
    def url(self):
        return f'{self.base_url}/account'

    def get_api_key_and_secret(self):
        grid_div = self.driver.find_element_by_xpath(self.DIV_BY_LABEL_TEMPLATE.format(label_text='API Key:'))
        elems = grid_div.find_elements_by_css_selector('div')
        return {'key': elems[0].text, 'secret': elems[1].text}

    def reset_api_key_and_secret(self):
        self.click_button('Reset Key', should_scroll_into_view=False)
        self.wait_for_element_present_by_id('approve-reset-api-key')
        self.click_button_by_id('approve-reset-api-key', should_scroll_into_view=False)
