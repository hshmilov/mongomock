from selenium.common.exceptions import NoSuchElementException
from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin

from ui_tests.pages.entities_page import EntitiesPage
from axonius.utils.wait import wait_until


@dataclass(frozen=True)
class ReportFrequency(DataClassJsonMixin):
    daily = 'period-daily'
    weekly = 'period-weekly'
    monthly = 'period-monthly'


@dataclass(frozen=True)
class ReportConfig(DataClassJsonMixin):
    report_name: str
    add_dashboard: bool = True
    queries: list = None
    add_scheduling: bool = False
    email_subject: str = None
    emails: list = None
    period: str = ReportFrequency.daily
    spaces: list = None
    period_config: object = None


class ReportsPage(EntitiesPage):
    NEW_REPORT_BUTTON = 'Add Report'
    REMOVE_REPORTS_BUTTON = 'Remove'
    SAFEGUARD_REMOVE_REPORTS_BUTTON_SINGLE = 'Remove Report'
    SAFEGUARD_REMOVE_REPORTS_BUTTON_MULTI = 'Remove Reports'
    REPORT_CSS = '.x-report'
    REPORT_NAME_ID = 'report_name'
    REPORT_FREQUENCY = 'report_frequency'
    SAVED_QUERY_CLASS = '.saved-query'
    QUERY_ADD_CLASS = '.query-add'
    QUERY_REMOVE_CLASS = '.query-remove'
    ADD_SCHEDULING_CHECKBOX = 'Email Configuration'
    INCLUDE_QUERIES_CHECKBOX = 'Include Saved Queries data'
    INCLUDE_DASHBOARD_CHECKBOX = 'Include dashboard charts'
    EMAIL_BOX_CSS = 'input.md-input__inner.md-chips-input__inner'
    EMAIL_BOX_RECIPIENTS = 'Recipients'
    EDIT_REPORT_XPATH = '//td[.//text()=\'{report_name}\']'
    REPORT_GENERATED_XPATH = '//td[.//text()=\'{report_name}\']/following::td/div'
    REPORT_TR_XPATH = '//td[.//text()=\'{report_name}\']/parent::tr'
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
    SELECT_PERIOD_TIME_CSS = '.send-hour .time-picker-text input'
    TIME_PERIOD_SELECTOR_CSS = '.v-time-picker-clock'
    TIME_PERIOD_TITLE_SELECTOR_CSS = '.v-time-picker-title'
    TIME_PERIOD_AMPM_TITLE_CSS = '.v-time-picker-title__ampm'
    TIME_PERIOD_TITLE_BUTTON_CSS = '.v-picker__title__btn'
    TIME_PERIOD_SELECTOR_XPATH = '//span[text()=\'{time}\']'
    TIME_PERIOD_CLOCK_CONTAINER_CSS = '.v-time-picker-clock__container'
    SELECT_WEEKDAY_CSS = '.send-day .x-select #weekly-day'
    SELECT_MONTHLYDAY_CSS = '.send-day .x-select #monthly-day'
    SELECT_DAY_VALUE_CSS = '.send-day .x-select .trigger-text'
    SELECT_DAY_CLEAR_CSS = '.send-day .x-select .trigger'
    BUTTON_CONTAINER_CSS = '.x-btn-container'
    SELECT_DAY_CSS = '.send-day .x-select'

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

    def click_remove_reports(self, confirm=False):
        if confirm:
            self.remove_selected_with_safeguard(self.SAFEGUARD_REMOVE_REPORTS_BUTTON_SINGLE,
                                                self.SAFEGUARD_REMOVE_REPORTS_BUTTON_MULTI)
        else:
            self.remove_selected_with_safeguard()

    def click_select_all_reports(self):
        self.toggle_select_all_rows_checkbox()

    def click_select_report(self, index):
        self.click_row_checkbox(index)

    def find_new_report_button(self):
        return self.get_enabled_button(self.NEW_REPORT_BUTTON)

    def find_remove_reports_button(self):
        return self.get_button(self.REMOVE_REPORTS_BUTTON, button_class='x-button link')

    def get_report_count(self):
        return self.count_entities()

    def is_disabled_new_report_button(self):
        return self.is_element_disabled(self.get_button(self.NEW_REPORT_BUTTON))

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
        return self.get_button(self.SEND_EMAIL_BUTTON_TEXT)

    def is_send_email_button_exists(self):
        try:
            self.find_send_email_button()
            return True
        except NoSuchElementException:
            return False

    def click_send_email(self):
        self.click_button(self.SEND_EMAIL_BUTTON_TEXT)

    def select_frequency(self, period):
        self.driver.find_element_by_id(period).click()

    def get_selected_day(self):
        day_elements = self.driver.find_elements_by_css_selector(self.SELECT_DAY_VALUE_CSS)
        for day_element in day_elements:
            if day_element.is_displayed():
                return day_element.text
        return ''

    def click_on_select_day(self):
        day_elements = self.driver.find_elements_by_css_selector(self.SELECT_DAY_VALUE_CSS)
        for day_element in day_elements:
            if day_element.is_displayed():
                day_element.click()

    def select_weekly_day(self, day):
        self.select_option_without_search(self.SELECT_WEEKDAY_CSS, self.DROPDOWN_SELECTED_OPTION_CSS, day)

    def select_monthly_day(self, day):
        self.select_option_without_search(self.SELECT_MONTHLYDAY_CSS, self.DROPDOWN_SELECTED_OPTION_CSS, day)

    def get_weekly_day(self):
        return self.driver.find_element_by_css_selector(self.SELECT_WEEKDAY_CSS).text

    def get_monthly_day(self):
        return self.driver.find_element_by_css_selector(self.SELECT_MONTHLYDAY_CSS).text

    def get_select_days(self):
        self.driver.find_element_by_css_selector(self.SELECT_DAY_CSS).click()
        try:
            for element in self.driver.find_elements_by_css_selector('.x-select-option'):
                yield element.text
        finally:
            self.driver.find_element_by_css_selector(self.SELECT_DAY_CSS).click()

    def select_frequency_time(self, send_time):
        send_time_parts = send_time.split(':')
        hours = int(send_time_parts[0])
        minutes = int(send_time_parts[1])
        ampm = 'AM'
        if hours >= 12:
            ampm = 'PM'
            hours -= 12
        if hours == 0:
            hours = 12

        self.fill_text_by_element(self.driver.find_element_by_css_selector(self.SELECT_PERIOD_TIME_CSS),
                                  f'{str(hours)}:{"{:0>2d}".format(minutes)}{ampm.lower()}', True)

    def is_frequency_set(self, period):
        if self.driver.find_element_by_id(self.REPORT_FREQUENCY):
            return self.driver.find_element_by_id(period).is_selected()
        return False

    def is_generated(self):
        return 'Last generated' in self.driver.find_element_by_css_selector(self.REPORT_TITLE_CSS).text

    def get_report_generated_date(self, report_name):
        self.refresh()
        return self.driver.find_element_by_xpath(self.REPORT_GENERATED_XPATH.format(report_name=report_name)).text

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
                   total_timeout=60 * 10, interval=2)
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
        self.wait_for_spinner_to_end()

    def get_report_id(self, report_name):
        return self.driver.find_element_by_xpath(self.REPORT_TR_XPATH.format(report_name=report_name))\
            .get_attribute('id')

    def select_saved_view(self, text, entity='Devices'):
        selected_option = self.select_option_without_search(self.SELECT_VIEW_ENTITY_CSS,
                                                            self.DROPDOWN_SELECTED_OPTION_CSS, entity)
        if not selected_option:
            self.close_dropdown()
            return None
        self.select_option(self.SELECT_VIEW_NAME_CSS, self.DROPDOWN_TEXT_BOX_CSS, self.DROPDOWN_SELECTED_OPTION_CSS,
                           text)
        return selected_option

    def select_saved_view_from_multiple(self, index, text, entity='Devices'):
        self.select_option_without_search_from_multiple(index, self.SELECT_VIEW_ENTITY_CSS,
                                                        self.DROPDOWN_SELECTED_OPTION_CSS, entity)
        self.select_option_from_multiple(index, self.SELECT_VIEW_NAME_CSS, self.DROPDOWN_TEXT_BOX_CSS,
                                         self.DROPDOWN_SELECTED_OPTION_CSS, text)

    def assert_select_saved_views_is_empty(self, index):
        self.assert_select_option_is_empty(index, self.SELECT_VIEW_ENTITY_CSS, self.DROPDOWN_SELECTED_OPTION_CSS)
        self.close_dropdown()

    def get_saved_view(self):
        return self.driver.find_element_by_css_selector(self.SELECT_VIEW_NAME_ELEMENT_CSS).text

    def find_email_sent_toaster(self):
        return self.wait_for_toaster('Email sent successfully')

    def is_report_download_shown(self):
        try:
            self.driver.find_element_by_id(self.REPORT_DOWNLOAD_ID)
        except NoSuchElementException:
            return False
        return True

    def click_report_download(self):
        self.driver.find_element_by_id(self.REPORT_DOWNLOAD_ID).click()

    def get_spaces_select(self):
        return self.find_element_following_label(self.SPACES_LABEL)

    def click_spaces_select(self):
        self.get_spaces_select().click()

    def get_spaces_select_placeholder(self):
        return self.get_spaces_select().find_element_by_tag_name('input').get_attribute('placeholder')

    def create_report(self,
                      report_config: ReportConfig,
                      wait_for_toaster=True):
        self.switch_to_page()
        self.wait_for_table_to_load()
        self.click_new_report()
        self.wait_for_spinner_to_end()
        self.fill_report_name(report_config.report_name)
        if report_config.add_dashboard:
            self.click_include_dashboard()
            if report_config.spaces:
                self.click_spaces_select()
                for space in report_config.spaces:
                    self.find_element_by_text(space).click()
        if report_config.queries:
            self.click_include_queries()
            self.select_saved_views(report_config.queries)
        if report_config.add_scheduling:
            self.config_scheduling(report_config)
        self.click_save()
        if wait_for_toaster:
            self.wait_for_report_is_saved_toaster()

    def select_saved_views(self, queries):
        for index, query in enumerate(queries):
            self.select_saved_view_from_multiple(index, query['name'], query['entity'])
            if index < len(queries) - 1:
                self.click_add_query()

    def config_scheduling(self, report_config):
        self.click_add_scheduling()
        self.fill_email_subject(report_config.email_subject)
        for email in report_config.emails:
            self.fill_email(email)
        self.select_frequency(report_config.period)
        if report_config.period_config:
            if report_config.period == ReportFrequency.weekly and report_config.period_config.get('week_day'):
                weekday = list(self.get_select_days())[report_config.period_config.get('week_day')]
                self.select_weekly_day(weekday)
            if report_config.period == ReportFrequency.monthly and report_config.period_config.get('monthly_day'):
                self.select_monthly_day(report_config.period_config.get('monthly_day'))
            if report_config.period_config.get('send_time'):
                self.select_frequency_time(report_config.period_config.get('send_time'))

    def wait_for_report_is_saved_toaster(self):
        self.wait_for_toaster(self.REPORT_IS_SAVED_TOASTER)
        self.wait_for_toaster_to_end(self.REPORT_IS_SAVED_TOASTER)

    def is_dashboard_checkbox_disabled(self):
        return self.is_element_has_disabled_class(self.find_element_parent_by_text(self.INCLUDE_DASHBOARD_CHECKBOX))

    def is_include_saved_queries_checkbox_disabled(self):
        return self.is_element_has_disabled_class(self.find_element_parent_by_text(self.INCLUDE_QUERIES_CHECKBOX))

    def is_saved_queries_disabled(self):
        if not self.is_include_saved_queries_checkbox_disabled():
            return False
        if 'checked' in self.find_element_parent_by_text(self.INCLUDE_QUERIES_CHECKBOX).get_attribute('class'):
            if not self.is_element_has_disabled_class(
                    self.driver.find_element_by_css_selector(self.SELECT_VIEW_ENTITY_ELEMENT_CSS)
            ):
                return False
            if not self.is_element_has_disabled_class(
                    self.driver.find_element_by_css_selector(self.SELECT_VIEW_NAME_ELEMENT_CSS)
            ):
                return False
        return True

    def is_email_config_disabled(self):
        return self.is_element_has_disabled_class(self.find_element_preceding_by_text(self.ADD_SCHEDULING_CHECKBOX))

    def is_email_subject_disabled(self):
        return not self.driver.find_element_by_id(self.EMAIL_SUBJECT_ID).is_enabled()

    def is_form_disabled(self):
        disabled_list = [self.is_dashboard_checkbox_disabled(),
                         self.is_include_saved_queries_checkbox_disabled(),
                         self.is_saved_queries_disabled(),
                         self.is_email_config_disabled(),
                         self.is_save_button_disabled()]
        if 'checked' in self.find_element_preceding_by_text(self.ADD_SCHEDULING_CHECKBOX).get_attribute('class'):
            disabled_list.append(self.is_email_subject_disabled())
        return all(disabled_list)

    def is_report_error(self, error_text=None):
        if not error_text:
            error_text = ''
        return error_text == self.driver.find_element_by_css_selector(self.ERROR_TEXT_CSS).text

    def wait_for_before_save_finished_toaster(self):
        self.wait_for_toaster_to_end(self.BEFORE_SAVE_MESSAGE)

    def is_name_already_exists_error_appear(self):
        return self.is_report_error(self.REPORT_NAME_DUPLICATE_ERROR)
