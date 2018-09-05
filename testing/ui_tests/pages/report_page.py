from selenium.webdriver.common.keys import Keys

from ui_tests.pages.entities_page import EntitiesPage


class ReportPage(EntitiesPage):
    EMAIL_BOX_CSS = 'input.vm-input__inner.vm-select-input__inner'

    @property
    def url(self):
        return f'{self.base_url}/report'

    @property
    def root_page_css(self):
        return 'li#reports.x-nested-nav-item'

    def fill_email(self, email):
        element = self.driver.find_element_by_css_selector(self.EMAIL_BOX_CSS)
        self.send_keys(element, email)
        self.send_keys(element, Keys.ENTER)

    def click_test_now(self):
        self.find_element_by_text('Test Now').click()

    def find_no_email_server_toaster(self):
        self.find_toaster('Problem testing report by email: No email server configured')

    def find_email_sent_toaster(self):
        self.find_toaster('Email with executive report was sent.')
