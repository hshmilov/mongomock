from selenium.common.exceptions import NoSuchElementException

from ui_tests.pages.entities_page import EntitiesPage
from axonius.utils.wait import wait_until


class ReportFrequency:
    daily = 'period-daily'
    weekly = 'period-weekly'
    monthly = 'period-monthly'


class ReportsPage(EntitiesPage):
    NEW_REPORT_BUTTON = '+ New Report'
    REMOVE_REPORTS_BUTTON = 'Remove'
    SAFEGUARD_REMOVE_REPORTS_BUTTON = 'Remove Reports'
    REPORT_CSS = '.x-report'
    REPORT_NAME_ID = 'report_name'
    REPORT_FREQUENCY = 'report_frequency'
    SAVED_QUERY_CLASS = '.saved-query'
    QUERY_ADD_CLASS = '.query-add'
    QUERY_REMOVE_CLASS = '.query-remove'
    ADD_SCHEDULING_CHECKBOX = 'Email Configuration'
    SAVE_BUTTON_ID = 'report_save'
    INCLUDE_QUERIES_CHECKBOX = 'Include Saved Queries data'
    INCLUDE_DASHBOARD_CHECKBOX = 'Include dashboard charts'
    EMAIL_BOX_CSS = 'input.md-input__inner.md-chips-input__inner'
    EMAIL_BOX_RECIPIENTS = 'Recipients'
    EDIT_REPORT_XPATH = '//div[@title=\'{report_name}\']'
    REPORT_GENERATED_XPATH = '//div[@title=\'{report_name}\']/parent::td/following::td/following::td//div'
    REPORT_TR_XPATH = '//div[@title=\'{report_name}\']/parent::td/parent::tr'
    EMAIL_SUBJECT_ID = 'mailSubject'
    SELECT_VIEW_ENTITY_ELEMENT_CSS = '.saved-query .x-select-symbol'
    SELECT_VIEW_ENTITY_CSS = '.saved-query .x-select-symbol .x-select-trigger'
    SELECT_VIEW_NAME_ELEMENT_CSS = '.saved-query .query-name'
    SELECT_VIEW_NAME_CSS = '.saved-query .query-name .x-select-trigger'
    SELECT_SAVED_VIEW_TEXT_CSS = 'div.trigger-text'
    EMAIL_DESCRIPTION_CSS = '.email-description'
    REPORT_TITLE_CSS = '.report-title'
    SEND_MAIL_BUTTON_ID = 'test-report'
    REPORT_DOWNLOAD_ID = 'reports_download'
    REPORT_IS_SAVED_TOASTER = 'Report is saved and being generated in the background'
    ERROR_TEXT_CSS = '.error-text'
    BEFORE_SAVE_MESSAGE = 'Saving the report...'
    REPORT_NAME_DUPLICATE_ERROR = 'Report name already taken by another report'
    SPACES_LABEL = 'Dashboard spaces'
    SEND_EMAIL_BUTTON_TEXT = 'Send Email'

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
        self.wait_for_spinner_to_end()

    def click_remove_reports(self):
        self.find_remove_reports_button().click()
        self.find_element_by_text(self.SAFEGUARD_REMOVE_REPORTS_BUTTON).click()

    def click_select_all_reports(self):
        self.select_all_current_page_rows_checkbox()

    def click_select_report(self, index):
        self.click_row_checkbox(index)

    def find_new_report_button(self):
        return self.get_button(self.NEW_REPORT_BUTTON)

    def find_remove_reports_button(self):
        return self.get_button(self.REMOVE_REPORTS_BUTTON, button_class='x-button link')

    def get_report_count(self):
        return self.count_entities()

    def is_disabled_new_report_button(self):
        return self.is_element_disabled(self.find_element_by_text(self.NEW_REPORT_BUTTON))

    def get_to_new_report_page(self):
        self.switch_to_page()
        self.click_new_report()
        self.wait_for_spinner_to_end()

    def fill_report_name(self, name):
        report_name_element = self.driver.find_element_by_id(self.REPORT_NAME_ID)
        self.fill_text_by_element(report_name_element, name)

    def click_include_queries(self):
        self.find_element_by_text(self.INCLUDE_QUERIES_CHECKBOX).click()

    def click_include_dashboard(self):
        self.find_element_by_text(self.INCLUDE_DASHBOARD_CHECKBOX).click()

    def is_include_dashboard(self):
        return self.is_toggle_selected(self.find_element_preceding_by_text(self.INCLUDE_DASHBOARD_CHECKBOX))

    def click_add_query(self):
        self.driver.find_element_by_css_selector(self.QUERY_ADD_CLASS).click()

    def click_remove_query(self, i):
        self.driver.find_elements_by_css_selector(self.QUERY_REMOVE_CLASS)[i].click()

    def get_queries_count(self):
        return len(self.driver.find_elements_by_css_selector(self.SAVED_QUERY_CLASS))

    def click_add_scheduling(self):
        self.find_element_by_text(self.ADD_SCHEDULING_CHECKBOX).click()

    def is_add_scheduling_selected(self):
        return self.is_toggle_selected(self.find_element_preceding_by_text(self.ADD_SCHEDULING_CHECKBOX))

    def fill_email_subject(self, subject):
        report_subject_element = self.driver.find_element_by_id(self.EMAIL_SUBJECT_ID)
        self.fill_text_by_element(report_subject_element, subject)

    def get_email_subject(self):
        report_subject_element = self.driver.find_element_by_id(self.EMAIL_SUBJECT_ID)
        return report_subject_element.get_attribute('value')

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

    def find_send_email_button(self):
        return self.find_element_by_text(self.SEND_EMAIL_BUTTON_TEXT)

    def is_send_email_button_exists(self):
        try:
            self.find_send_email_button()
            return True
        except NoSuchElementException:
            return False

    def click_send_email(self):
        self.find_send_email_button().click()

    def assert_screen_is_restricted(self):
        self.switch_to_page_allowing_failure()
        self.find_element_by_text('You do not have permission to access the Reports screen')
        self.click_ok_button()

    def select_frequency(self, period):
        self.driver.find_element_by_id(period).click()

    def is_frequency_set(self, period):
        if self.driver.find_element_by_id(self.REPORT_FREQUENCY):
            return self.driver.find_element_by_id(period).is_selected()
        return False

    def is_generated(self):
        return 'Last generated' in self.driver.find_element_by_css_selector(self.REPORT_TITLE_CSS).text

    def get_report_generated_date(self, report_name):
        self.refresh()
        return self.driver.find_element_by_xpath(self.REPORT_GENERATED_XPATH.format(report_name=report_name)).text

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
        self.wait_for_table_to_load()

    def wait_for_send_mail_button(self):
        self.wait_for_element_present_by_id(self.SEND_MAIL_BUTTON_ID)

    def get_table_number_of_rows(self):
        self.wait_for_table_to_load()
        return len(self.get_all_table_rows())

    def click_report(self, report_name):
        self.driver.find_element_by_xpath(self.EDIT_REPORT_XPATH.format(report_name=report_name)).click()
        self.wait_for_element_present_by_css(self.REPORT_CSS)

    def get_report_id(self, report_name):
        return self.driver.find_element_by_xpath(self.REPORT_TR_XPATH.format(report_name=report_name))\
            .get_attribute('id')

    def select_saved_view(self, text, entity='Devices'):
        self.select_option_without_search(self.SELECT_VIEW_ENTITY_CSS, self.DROPDOWN_SELECTED_OPTION_CSS, entity)
        self.select_option(self.SELECT_VIEW_NAME_CSS, self.DROPDOWN_TEXT_BOX_CSS, self.DROPDOWN_SELECTED_OPTION_CSS,
                           text)

    def select_saved_view_from_multiple(self, index, text, entity='Devices'):
        self.select_option_without_search_from_multiple(index, self.SELECT_VIEW_ENTITY_CSS,
                                                        self.DROPDOWN_SELECTED_OPTION_CSS, entity)
        self.select_option_from_multiple(index, self.SELECT_VIEW_NAME_CSS, self.DROPDOWN_TEXT_BOX_CSS,
                                         self.DROPDOWN_SELECTED_OPTION_CSS, text)

    def get_saved_view(self):
        return self.driver.find_element_by_css_selector(self.SELECT_VIEW_NAME_ELEMENT_CSS).text

    def find_email_sent_toaster(self):
        return self.wait_for_toaster('Email sent successfully')

    def is_save_button_disabled(self):
        return self.is_element_disabled(self.get_save_button())

    def is_report_download_shown(self):
        try:
            self.driver.find_element_by_id(self.REPORT_DOWNLOAD_ID)
        except NoSuchElementException:
            return False
        return True

    def click_report_download(self):
        self.driver.find_element_by_id(self.REPORT_DOWNLOAD_ID).click()

    def click_spaces_select(self):
        self.find_element_following_label(self.SPACES_LABEL).click()

    def get_spaces(self):
        element = self.find_element_following_label(self.SPACES_LABEL)
        return [elm.get_attribute('value')
                for elm in element.find_elements_by_css_selector('.md-select .md-input.md-select-value')]

    def get_spaces_options(self):
        self.click_spaces_select()
        self.wait_for_element_present_by_css('.md-list-item-text')
        return [e.text for e in self.driver.find_elements_by_css_selector('.md-list-item-text')]

    def create_report(self, report_name, add_dashboard=True, queries=None, add_scheduling=False, email_subject=None,
                      emails=None, period=ReportFrequency.daily, wait_for_toaster=True, spaces=None):
        self.switch_to_page()
        self.wait_for_table_to_load()
        self.click_new_report()
        self.wait_for_spinner_to_end()
        self.fill_report_name(report_name)
        if add_dashboard:
            self.click_include_dashboard()
            if spaces:
                self.click_spaces_select()
                for space in spaces:
                    self.find_element_by_text(space).click()
        if queries:
            self.click_include_queries()
            for index, query in enumerate(queries):
                self.select_saved_view_from_multiple(index, query['name'], query['entity'])
                if index < len(queries) - 1:
                    self.click_add_query()
        if add_scheduling:
            self.click_add_scheduling()
            self.fill_email_subject(email_subject)
            for email in emails:
                self.fill_email(email)
            self.select_frequency(period)
        self.click_save()
        if wait_for_toaster:
            self.wait_for_report_is_saved_toaster()

    def wait_for_report_is_saved_toaster(self):
        self.wait_for_toaster(self.REPORT_IS_SAVED_TOASTER)
        self.wait_for_toaster_to_end(self.REPORT_IS_SAVED_TOASTER)

    def is_dashboard_checkbox_disabled(self):
        return self.is_element_disabled(self.find_element_parent_by_text(self.INCLUDE_DASHBOARD_CHECKBOX))

    def is_include_saved_queries_checkbox_disabled(self):
        return self.is_element_disabled(self.find_element_parent_by_text(self.INCLUDE_QUERIES_CHECKBOX))

    def is_saved_queries_disabled(self):
        if not self.is_element_disabled(self.driver.find_element_by_css_selector(self.SELECT_VIEW_ENTITY_ELEMENT_CSS)):
            return False
        return self.is_element_disabled(self.driver.find_element_by_css_selector(self.SELECT_VIEW_NAME_ELEMENT_CSS))

    def is_email_config_disabled(self):
        return self.is_element_disabled(self.find_element_preceding_by_text(self.ADD_SCHEDULING_CHECKBOX))

    def is_email_subject_disabled(self):
        return not self.driver.find_element_by_id(self.EMAIL_SUBJECT_ID).is_enabled()

    def is_form_disabled(self):
        disabled_list = [self.is_dashboard_checkbox_disabled(),
                         self.is_include_saved_queries_checkbox_disabled(),
                         self.is_saved_queries_disabled(),
                         self.is_email_config_disabled(),
                         self.is_email_subject_disabled(),
                         self.is_save_button_disabled()]
        return all(disabled_list)

    def is_report_error(self, error_text=None):
        if not error_text:
            error_text = ''
        return error_text == self.driver.find_element_by_css_selector(self.ERROR_TEXT_CSS).text

    def wait_for_before_save_finished_toaster(self):
        self.wait_for_toaster_to_end(self.BEFORE_SAVE_MESSAGE)

    def is_name_already_exists_error_appear(self):
        return self.is_report_error(self.REPORT_NAME_DUPLICATE_ERROR)
