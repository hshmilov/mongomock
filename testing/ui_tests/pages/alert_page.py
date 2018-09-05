from ui_tests.pages.entities_page import EntitiesPage


class AlertPage(EntitiesPage):
    ALERT_NAME_ID = 'alert_name'
    NEW_ALERT_BUTTON = '+ New Alert'

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
