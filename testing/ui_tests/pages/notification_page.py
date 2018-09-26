import datetime
import logging
from typing import List
from urllib.parse import urljoin

from ui_tests.pages.page import Page
from axonius.utils.wait import wait_until

logger = logging.getLogger(f'axonius.{__name__}')


class NotificationPage(Page):
    NOTIFICATION_PEEK_CSS = 'div.x-dropdown.notification-peek'
    NOTIFICATION_PEEK_TITLE = 'div.d-flex'
    NOTIFICATION_PEEK_TIMESTAMP_CSS = 'div.c-grey-4'

    @property
    def root_page_css(self):
        pass

    @property
    def url(self):
        return f'{self.base_url}/notification'

    def switch_to_page(self):
        logger.info(f'Switching to {self.url}')
        full_url = urljoin(self.base_url, self.url)
        self.driver.get(full_url)

    def get_peek_notifications(self):
        self.driver.find_element_by_css_selector(self.NOTIFICATION_PEEK_CSS).click()

        def get_expanded_notification(notification_text: str) -> List[str]:
            # notification text looks like this "bla bla bla (X)" where X is a number
            count = int(notification_text[notification_text.rfind('(') + 1: -1])
            return [notification_text] * count

        peek_notifications = [get_expanded_notification(element.text) for
                              element in
                              self.driver.find_elements_by_css_selector(self.NOTIFICATION_PEEK_TITLE)]

        # flatten list
        peek_notifications = [item for sublist in peek_notifications for item in sublist]

        self.driver.find_element_by_css_selector(self.NOTIFICATION_PEEK_CSS).click()
        return peek_notifications

    def is_text_in_peek_notifications(self, text):
        return any(text in notification for notification in self.get_peek_notifications())

    def get_timestamps_in_peek_notifications(self):
        elements = self.driver.find_elements_by_css_selector(self.NOTIFICATION_PEEK_TIMESTAMP_CSS)
        return [element.text for element in elements]

    def get_rows_from_notification_table(self):
        rows = self.driver.find_elements_by_css_selector('tr.x-row.clickable')
        # first one is the title row
        return [line.text for line in rows[1:]]

    @staticmethod
    def get_timestamps_from_rows(rows):
        return [line.split('\n')[0] for line in rows]

    @staticmethod
    def convert_timestamp_to_datetime(timestamp):
        # timestamp format: 9/17/2018 7:59:34 PM
        return datetime.datetime.strptime(timestamp, '%m/%d/%Y %I:%M:%S %p')

    def verify_amount_of_notifications(self, count: int):
        """
        Waits until the amount of notifications is the amount specified, or fails
        """
        wait_until(lambda: len(self.get_peek_notifications()) == count)
