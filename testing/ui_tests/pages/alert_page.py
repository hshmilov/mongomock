from ui_tests.pages.entities_page import EntitiesPage
from ui_tests.pages.page import X_BODY


class AlertPage(EntitiesPage):
    ALERT_NAME_ID = 'alert_name'
    NEW_ALERT_BUTTON = '+ New Alert'
    SELECT_SAVED_QUERY_CSS = 'div#alert_query.x-select-trigger'
    SAVED_QUERY_INPUT_CSS = 'input.input-value'
    SAVED_QUERY_OPTION_CSS = 'div.x-select-option'
    ALERTS_CHECKBOX = 'div.x-checkbox-container'
    INCREASE_ID = 'alert_above'
    EDIT_ALERT_XPATH = '//div[@title=\'{alert_name}\']'
    SELECT_SAVED_QUERY_TEXT_CSS = 'div.trigger-text'
    SEVERITY_WARNING_RADIO = '#SeverityWarning'

    @property
    def url(self):
        return f'{self.base_url}/alert'

    @property
    def root_page_css(self):
        return 'li#alerts.x-nested-nav-item'

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
        element = self.find_element_by_text('Send an Email')
        self.scroll_into_view(element, X_BODY)
        element.click()

    def find_missing_email_server_notification(self):
        return self.find_element_by_text('In order to send alerts through mail, define the server under settings')

    def check_alert_checkbox(self, text):
        self.find_element_by_text(text).click()

    def check_new(self):
        self.check_alert_checkbox('New entities were added to query result')

    def check_previous(self):
        self.check_alert_checkbox('Previous entities were subtracted from query results')

    def check_above(self):
        self.check_alert_checkbox('The number of query results is above')

    def check_below(self):
        self.check_alert_checkbox('The number of query results is below')

    def check_every_discovery(self):
        self.check_alert_checkbox('Every discovery cycle')

    def fill_below_value(self, value):
        self.fill_text_field_by_element_id('TriggerBelow', value)

    def check_push_system_notification(self):
        self.check_alert_checkbox('Push a system notification')

    def check_notify_syslog(self):
        self.check_alert_checkbox('Notify syslog')

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
        self.driver.find_element_by_css_selector(self.SEVERITY_WARNING_RADIO).click()

    def fill_above(self, value):
        self.fill_text_field_by_element_id(self.INCREASE_ID, value)

    def get_above_value(self):
        return self.driver.find_element_by_id(self.INCREASE_ID).get_attribute('value')

    def edit_alert(self, alert_name):
        self.driver.find_element_by_xpath(self.EDIT_ALERT_XPATH.format(alert_name=alert_name)).click()

    def get_saved_query_text(self):
        return self.driver.find_element_by_css_selector(self.SELECT_SAVED_QUERY_TEXT_CSS).get_attribute('title')

    def assert_screen_is_restricted(self):
        self.switch_to_page()
        self.find_element_by_text('You do not have permission to access the Alerts screen')
        self.click_ok_button()
