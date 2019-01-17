import time

from selenium.common.exceptions import NoSuchElementException

from ui_tests.pages.entities_page import EntitiesPage
from ui_tests.pages.page import X_BODY


class Severity:
    Info = '#SeverityInfo'
    Warning = '#SeverityWarning'
    Error = '#SeverityError'


class Period:
    EveryDiscovery = '#EveryPhasePeriod'
    Daily = '#DailyPeriod'
    Weekly = '#WeeklyPeriod'


class Trigger:
    EveryDiscoveryCycle = 'Any results'
    NewEntries = 'New entities were added to query results'
    PreviousEntries = 'Previous entities were subtracted from query results'
    Above = 'The number of query results is above'
    Below = 'The number of query results is below'


class Action:
    SendEmail = 'Send an Email'
    PushNotification = 'Push a system notification'
    Syslog = 'Notify syslog'
    TagAllEntities = 'Tag all entities'
    TagNewEntities = 'Tag new entities'


class AlertPage(EntitiesPage):
    ALERT_NAME_ID = 'alert_name'
    NEW_ALERT_BUTTON = '+ New Alert'
    SELECT_SAVED_QUERY_CSS = 'div#alert_query.x-select-trigger'
    SAVED_QUERY_INPUT_CSS = 'input.input-value'
    SAVED_QUERY_OPTION_CSS = 'div.x-select-option'
    ALERTS_CHECKBOX = 'div.x-checkbox-container'
    ABOVE_ID = 'alert_above'
    BELOW_ID = 'alert_below'
    EDIT_ALERT_XPATH = '//div[@title=\'{alert_name}\']'
    SELECT_SAVED_QUERY_TEXT_CSS = 'div.trigger-text'
    SEND_AN_EMAIL = 'Send an Email'

    @property
    def url(self):
        return f'{self.base_url}/alerts'

    @property
    def root_page_css(self):
        return 'li#alerts.x-nav-item'

    def find_checkbox_by_label(self, text):
        return self.driver.find_element_by_xpath(self.CHECKBOX_XPATH_TEMPLATE.format(label_text=text))

    def click_new_alert(self):
        self.wait_for_spinner_to_end()
        self.wait_for_element_present_by_text(self.NEW_ALERT_BUTTON)
        self.find_new_alert_button().click()
        self.wait_for_table_to_load()

    def find_new_alert_button(self):
        return self.find_element_by_text(self.NEW_ALERT_BUTTON)

    def fill_alert_name(self, name):
        self.fill_text_field_by_element_id(self.ALERT_NAME_ID, name)

    def click_send_an_email(self):
        element = self.find_element_by_text(Action.SendEmail)
        self.scroll_into_view(element, X_BODY)
        element.click()

    def click_tag_all_entities(self):
        element = self.find_element_by_text(Action.TagAllEntities)
        self.scroll_into_view(element, X_BODY)
        element.click()

    def click_tag_new_entities(self):
        element = self.find_element_by_text(Action.TagNewEntities)
        self.scroll_into_view(element, X_BODY)
        element.click()

    def fill_tag_all_text(self, tag_text):
        self.fill_text_field_by_element_id('tagAllName', tag_text)

    def fill_tag_new_text(self, tag_text):
        self.fill_text_field_by_element_id('tagNew', tag_text)

    def find_missing_email_server_notification(self):
        return self.find_element_by_text('In order to send alerts through mail, define the server under settings')

    def check_alert_checkbox(self, text):
        self.find_element_by_text(text).click()

    def check_new(self):
        self.check_alert_checkbox(Trigger.NewEntries)

    def check_previous(self):
        self.check_alert_checkbox(Trigger.PreviousEntries)

    def check_above(self):
        self.check_alert_checkbox(Trigger.Above)

    def check_below(self):
        self.check_alert_checkbox(Trigger.Below)

    def check_every_discovery(self):
        try:
            self.check_alert_checkbox(Trigger.EveryDiscoveryCycle)
        except NoSuchElementException:
            # The above is new behaviour and will not work on versions up to 1.15
            # Rollback to previous behaviour
            self.check_alert_checkbox('Every discovery cycle')

    def check_push_system_notification(self):
        self.check_alert_checkbox(Action.PushNotification)

    def check_notify_syslog(self):
        self.check_alert_checkbox(Action.Syslog)

    def select_saved_query(self, text):
        self.driver.find_element_by_css_selector(self.SELECT_SAVED_QUERY_CSS).click()
        self.fill_text_field_by_css_selector(self.SAVED_QUERY_INPUT_CSS, text)
        self.wait_for_element_present_by_css(self.SAVED_QUERY_OPTION_CSS).click()

    def click_save_button(self):
        # Ugly but will do for now
        button = self.driver.find_elements_by_css_selector('button.x-btn')[1]
        assert button.text == 'Save'
        button.click()

    def select_all_alerts(self):
        self.driver.find_element_by_css_selector(self.ALERTS_CHECKBOX).click()

    def remove_selected_alerts(self):
        self.find_element_by_text('Remove').click()

    def choose_severity_warning(self):
        self.driver.find_element_by_css_selector(Severity.Warning).click()

    def choose_period(self, period):
        self.driver.find_element_by_css_selector(period).click()

    def fill_above_value(self, value):
        self.fill_text_field_by_element_id(self.ABOVE_ID, value)

    def get_above_value(self):
        return self.driver.find_element_by_id(self.ABOVE_ID).get_attribute('value')

    def fill_below_value(self, value):
        self.fill_text_field_by_element_id(self.BELOW_ID, value)

    def edit_alert(self, alert_name):
        self.driver.find_element_by_xpath(self.EDIT_ALERT_XPATH.format(alert_name=alert_name)).click()

    def get_saved_query_text(self):
        return self.driver.find_element_by_css_selector(self.SELECT_SAVED_QUERY_TEXT_CSS).get_attribute('title')

    def assert_screen_is_restricted(self):
        self.switch_to_page()
        self.find_element_by_text('You do not have permission to access the Alerts screen')
        self.click_ok_button()

    def create_basic_alert(self, alert_name, alert_query):
        self.switch_to_page()
        # for some reason, this switch_to_page doesn't work from here sometimes
        time.sleep(1)
        self.switch_to_page()
        self.click_new_alert()
        self.wait_for_spinner_to_end()
        self.fill_alert_name(alert_name)
        self.select_saved_query(alert_query)

    def create_outputting_notification_alert(self,
                                             alert_name,
                                             alert_query,
                                             new=True,
                                             previous=True,
                                             every_discovery=True,
                                             above=0,
                                             below=0):

        self.create_basic_alert(alert_name, alert_query)
        if new:
            self.check_new()
        if previous:
            self.check_previous()
        if every_discovery:
            self.check_every_discovery()
        if above:
            self.check_above()
            self.fill_above_value(above)
        if below:
            self.check_below()
            self.fill_below_value(below)

        self.check_push_system_notification()
        self.click_save_button()
        self.wait_for_spinner_to_end()
        self.wait_for_table_to_load()

    def create_outputting_notification_above(self, alert_name, alert_query, above):
        self.create_outputting_notification_alert(alert_name,
                                                  alert_query,
                                                  new=False,
                                                  previous=False,
                                                  every_discovery=False,
                                                  above=above,
                                                  below=0)

    def create_outputting_notification_below(self, alert_name, alert_query, below):
        self.create_outputting_notification_alert(alert_name,
                                                  alert_query,
                                                  new=False,
                                                  previous=False,
                                                  every_discovery=False,
                                                  above=0,
                                                  below=below)

    def is_severity_selected(self, severity):
        return self.driver.find_element_by_css_selector(severity).is_selected()

    def is_period_selected(self, period):
        return self.driver.find_element_by_css_selector(period).is_selected()

    def is_action_selected(self, action):
        element = self.find_checkbox_container_by_label(action)
        return self.is_toggle_selected(element)

    def is_trigger_selected(self, trigger):
        element = self.find_checkbox_container_by_label(trigger)
        return element.get_attribute('class') == 'x-checkbox grid-span2 x-checked'

    def find_checkbox_container_by_label(self, label_text):
        return self.driver.find_element_by_xpath(self.DIV_BY_LABEL_TEMPLATE.format(label_text=label_text))
