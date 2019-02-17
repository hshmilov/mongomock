from selenium.webdriver.common.keys import Keys

from ui_tests.pages.entities_page import EntitiesPage


class ReportFrequency:
    daily = 'period-daily'
    weekly = 'period-weekly'
    monthly = 'period-monthly'


class ReportPage(EntitiesPage):
    EMAIL_BOX_CSS = 'input.vm-input__inner.vm-select-input__inner'

    @property
    def url(self):
        return f'{self.base_url}/reports'

    @property
    def root_page_css(self):
        return 'li#reports.x-nav-item'

    def fill_email(self, email):
        element = self.driver.find_element_by_css_selector(self.EMAIL_BOX_CSS)
        self.send_keys(element, email)
        self.send_keys(element, Keys.ENTER)

    def get_email(self):
        return self.driver.find_element_by_css_selector('span.vm-select__tags-text').text

    def click_test_now(self):
        self.find_element_by_text('Test Now').click()

    def find_no_email_server_toaster(self):
        self.find_toaster('Problem testing report by email: No email server configured')

    def find_email_sent_toaster(self):
        self.find_toaster('Email with executive report was sent.')

    def assert_screen_is_restricted(self):
        self.switch_to_page_allowing_failure()
        self.find_element_by_text('You do not have permission to access the Reports screen')
        self.click_ok_button()

    def select_frequency(self, period):
        self.driver.find_element_by_id(period).click()

    def is_frequency_set(self, perdiod):
        return self.driver.find_element_by_id(perdiod).is_selected()

    def click_save(self):
        try:
            self.click_button('Save')
        except Exception:
            # safe to remove after 1.14
            self.click_button('Save', call_space=False)
