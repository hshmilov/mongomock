from selenium.common.exceptions import NoSuchElementException

from ui_tests.pages.entities_page import EntitiesPage
from axonius.utils.wait import wait_until


class ReportFrequency:
    daily = 'period-daily'
    weekly = 'period-weekly'
    monthly = 'period-monthly'


class ReportsPage(EntitiesPage):
    NEW_REPORT_BUTTON = '+ New Report'
    REPORT_CSS = '.x-report'
    REPORT_NAME_ID = 'report_name'
    REPORT_SCHEDULE = 'report_schedule'
    SAVED_QUERY_CLASS = '.saved-query'
    QUERY_ADD_CLASS = '.query-add'
    QUERY_REMOVE_CLASS = '.query-remove'
    ADD_SCHEDULING_CHECKBOX = 'Email Configuration'
    ADD_SCHEDULING_ID = 'report_schedule'
    SAVE_BUTTON_ID = 'save-report'
    INCLUDE_QUERIES_CHECKBOX = 'Include Saved Queries data'
    INCLUDE_DASHBOARD_CHECKBOX = 'Include dashboard charts'
    EMAIL_BOX_CSS = 'input.md-input__inner.md-chips-input__inner'
    EMAIL_BOX_RECIPIENTS = 'Recipients'
    EDIT_REPORT_XPATH = '//div[@title=\'{report_name}\']'
    EMAIL_SUBJECT_ID = 'mailSubject'
    SELECT_VIEW_ENTITY_CSS = '.saved-query .x-select-symbol .x-select-trigger'
    SELECT_VIEW_NAME_CSS = '.saved-query .query-name .x-select-trigger'
    SELECT_SAVED_VIEW_TEXT_CSS = 'div.trigger-text'
    EMAIL_DESCRIPTION_CSS = '.email-description'
    REPORT_TITLE_CSS = '.report-title'
    SEND_MAIL_BUTTON_ID = 'test-report'

    @property
    def url(self):
        return f'{self.base_url}/reports'

    @property
    def root_page_css(self):
        return 'li#reports.x-nav-item'

    def click_new_report(self):
        self.wait_for_spinner_to_end()
        self.wait_for_table_to_load()
        self.wait_for_element_present_by_text(self.NEW_REPORT_BUTTON)
        self.find_new_report_button().click()
        self.wait_for_element_present_by_css(self.REPORT_CSS)

    def find_new_report_button(self):
        return self.get_button(self.NEW_REPORT_BUTTON)

    def is_disabled_new_report_button(self):
        return self.is_element_disabled(self.find_element_by_text(self.NEW_REPORT_BUTTON))

    def get_to_new_report_page(self):
        self.switch_to_page()
        self.click_new_report()

    def fill_report_name(self, name):
        report_name_element = self.driver.find_element_by_id(self.REPORT_NAME_ID)
        self.fill_text_by_element(report_name_element, name)

    def click_include_queries(self):
        self.find_element_by_text(self.INCLUDE_QUERIES_CHECKBOX).click()

    def click_include_dashboard(self):
        self.find_element_by_text(self.INCLUDE_DASHBOARD_CHECKBOX).click()

    def click_add_query(self):
        self.driver.find_element_by_css_selector(self.QUERY_ADD_CLASS).click()

    def click_remove_query(self, i):
        self.driver.find_elements_by_css_selector(self.QUERY_REMOVE_CLASS)[i].click()

    def get_queries_count(self):
        return len(self.driver.find_elements_by_css_selector(self.SAVED_QUERY_CLASS))

    def click_add_scheduling(self):
        self.find_element_by_text(self.ADD_SCHEDULING_CHECKBOX).click()

    def fill_email_subject(self, subject):
        report_subject_element = self.driver.find_element_by_id(self.EMAIL_SUBJECT_ID)
        self.fill_text_by_element(report_subject_element, subject)

    def fill_email(self, email):
        element = self.find_chips_by_label(self.EMAIL_BOX_RECIPIENTS)
        self.fill_text_by_element(element, email)
        self.key_down_enter(element)

    def edit_email(self, new_email, index=0):
        self.find_chips_values_by_label(self.EMAIL_BOX_RECIPIENTS)[index].click()
        self.fill_email(new_email)

    def get_emails(self):
        elements = self.find_chips_values_by_label(self.EMAIL_BOX_RECIPIENTS)
        return [element.text for element in elements]

    def click_send_email(self):
        self.find_element_by_text('Send Email').click()

    def assert_screen_is_restricted(self):
        self.switch_to_page_allowing_failure()
        self.find_element_by_text('You do not have permission to access the Reports screen')
        self.click_ok_button()

    def select_frequency(self, period):
        self.driver.find_element_by_id(period).click()

    def is_frequency_set(self, period):
        if self.is_toggle_selected(self.driver.find_element_by_id(self.REPORT_SCHEDULE)):
            return self.driver.find_element_by_id(period).is_selected()
        return False

    def is_generated(self):
        return 'Last generated' in self.driver.find_element_by_css_selector(self.REPORT_TITLE_CSS).text

    def get_save_button(self):
        return self.driver.find_element_by_id(self.SAVE_BUTTON_ID)

    def click_save(self):
        self.click_button(self.SAVE_BUTTON)

    def wait_for_email_description(self):
        self.wait_for_element_present_by_css(self.EMAIL_DESCRIPTION_CSS)

    def click_report_and_check_generation(self, report_name):
        self.refresh()
        try:
            self.wait_for_table_to_load()
            self.click_report(report_name)
            self.wait_for_spinner_to_end()
            return self.is_generated()
        except NoSuchElementException:
            return False

    def wait_for_report_generation(self, report_name):
        wait_until(lambda: self.click_report_and_check_generation(report_name),
                   total_timeout=60 * 3, interval=2)
        self.refresh()

    def wait_for_send_mail_button(self):
        self.wait_for_element_present_by_id(self.SEND_MAIL_BUTTON_ID)

    def get_table_number_of_rows(self):
        self.wait_for_table_to_load()
        return len(self.get_all_table_rows())

    def click_report(self, report_name):
        self.driver.find_element_by_xpath(self.EDIT_REPORT_XPATH.format(report_name=report_name)).click()
        self.wait_for_element_present_by_css(self.REPORT_CSS)

    def select_saved_view(self, text, entity='Devices'):
        self.select_option_without_search(self.SELECT_VIEW_ENTITY_CSS, self.DROPDOWN_SELECTED_OPTION_CSS, entity)
        self.select_option(self.SELECT_VIEW_NAME_CSS, self.DROPDOWN_TEXT_BOX_CSS, self.DROPDOWN_SELECTED_OPTION_CSS,
                           text)

    def find_email_sent_toaster(self):
        return self.wait_for_toaster('Email sent successfully')

    def is_save_button_disabled(self):
        return self.is_element_disabled(self.get_save_button())
