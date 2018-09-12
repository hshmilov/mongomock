from ui_tests.pages.page import Page


class NotificationPage(Page):
    NOTIFICATION_PEEK_CSS = 'div.x-dropdown.notification-peek'
    NOTIFICATION_PEEK_TITLE = 'div.notification-title'

    @property
    def root_page_css(self):
        pass

    @property
    def url(self):
        pass

    def get_peek_notifications(self):
        self.driver.find_element_by_css_selector(self.NOTIFICATION_PEEK_CSS).click()
        peek_notifications = [element.text for
                              element in
                              self.driver.find_elements_by_css_selector(self.NOTIFICATION_PEEK_TITLE)]
        self.driver.find_element_by_css_selector(self.NOTIFICATION_PEEK_CSS).click()
        return peek_notifications

    def is_text_in_peek_notifications(self, text):
        return any(text in notification for notification in self.get_peek_notifications())
