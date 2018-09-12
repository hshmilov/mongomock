from ui_tests.pages.entities_page import EntitiesPage


class AlertPage(EntitiesPage):
    ALERT_NAME_ID = 'alert_name'
    NEW_ALERT_BUTTON = '+ New Alert'
    SELECT_SAVED_QUERY_CSS = 'div#alert_query.x-select-trigger'
    SAVED_QUERY_INPUT_CSS = 'input.input-value'
    SAVED_QUERY_OPTION_CSS = 'div.x-select-option'
    ALERTS_CHECKBOX = 'div.x-checkbox-container'

    @property
    def url(self):
        return f'{self.base_url}/alert'

    @property
    def root_page_css(self):
        return 'li#alerts.x-nested-nav-item'

    def click_new_alert(self):
        self.wait_for_spinner_to_end()
        self.wait_for_element_present_by_text(self.NEW_ALERT_BUTTON)
        self.find_element_by_text(self.NEW_ALERT_BUTTON).click()

    def fill_alert_name(self, name):
        self.fill_text_field_by_element_id(self.ALERT_NAME_ID, name)

    def click_send_an_email(self):
        element = self.find_element_by_text('Send an Email')
        self.scroll_into_view(element)
        element.click()

    def find_missing_email_server_notification(self):
        return self.find_element_by_text('In order to send alerts through mail, define the server under settings')

    def check_alert_checkbox(self, text):
        self.find_element_by_text(text).click()

    def check_increased(self):
        self.check_alert_checkbox('Increased')

    def check_decreased(self):
        self.check_alert_checkbox('Decreased')

    def check_not_changed(self):
        self.check_alert_checkbox('Not Changed')

    def check_push_system_notification(self):
        self.check_alert_checkbox('Push a system notification')

    def select_saved_query(self, text):
        self.driver.find_element_by_css_selector(self.SELECT_SAVED_QUERY_CSS).click()
        self.fill_text_field_by_css_selector(self.SAVED_QUERY_INPUT_CSS, text)
        self.driver.find_element_by_css_selector(self.SAVED_QUERY_OPTION_CSS).click()

    def click_save_button(self):
        # Ugly but will do for now
        button = self.driver.find_elements_by_css_selector('a.x-btn')[1]
        assert button.text == 'Save'
        button.click()

    def select_all_alerts(self):
        self.driver.find_element_by_css_selector(self.ALERTS_CHECKBOX).click()

    def remove_selected_alerts(self):
        self.find_element_by_text('Remove').click()
