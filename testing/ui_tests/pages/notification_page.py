import datetime
import logging
import time
from typing import List
from urllib.parse import urljoin

from retrying import retry

from ui_tests.pages.page import Page
from axonius.utils.wait import wait_until

logger = logging.getLogger(f'axonius.{__name__}')


class NotificationPage(Page):
    NOTIFICATION_PEEK_CSS = 'div.x-dropdown.x-notification-peek'
    NOTIFICATION_PEEK_TIMESTAMP_CSS = 'div.c-grey-4'
    NOTIFICATION_COUNT_CSS = 'div.badge'
    NOTIFICATION_VIEW_ALL_BUTTON_CLASS = 'x-button link'
    NOTIFICATION_VIEW_ALL_TEXT = 'View All'

    # The first one is the title for the whole peek,
    # the 2nd is for each notification in the peek.
    NOTIFICATIONS_PEEK_TITLE = 'h5.mb-8'
    NOTIFICATION_PEEK_TITLE = 'div.d-flex'

    @property
    def root_page_css(self):
        pass

    @property
    def url(self):
        return f'{self.base_url}/notifications'

    def switch_to_page(self):
        logger.info(f'Switching to {self.url}')
        full_url = urljoin(self.base_url, self.url)
        self.driver.get(full_url)

    def click_notification_peek(self):
        self.driver.find_element_by_css_selector(self.NOTIFICATION_PEEK_CSS).click()

    def click_view_notifications(self):
        assert self.is_peek_open(), 'View notifications must be called with peek open'
        self.click_button(text=self.NOTIFICATION_VIEW_ALL_TEXT,
                          button_class=self.NOTIFICATION_VIEW_ALL_BUTTON_CLASS,
                          call_space=False)
        # wait for notification_page to load
        self.wait_for_table_to_load()

    def click_notification(self, name):
        assert self.is_peek_open(), 'View notifications must be called with peek open'
        self.find_element_by_text(f'"{name}"').click()

    def is_peek_open(self):
        return bool(self.driver.find_elements_by_css_selector(self.NOTIFICATIONS_PEEK_TITLE))

    def get_count(self):
        elements = self.driver.find_elements_by_css_selector(self.NOTIFICATION_COUNT_CSS)
        if not elements:
            # No badge -> no new notifications
            return 0

        assert len(elements) == 1, 'Multiple notification badge candidates found'

        return int(elements[0].text)

    @retry(stop_max_attempt_number=100, wait_fixed=100)
    def wait_for_count(self, assert_count: int, msg='assertion failed'):
        assert self.get_count() == assert_count, msg

        # The reason for the sleep here is because the count of notifications and the notifications
        # themselves may arrive at different times, so we want to make sure they have actually arrived
        # and there's no easy GUI way to do it
        time.sleep(5)

    def get_peek_notifications(self):
        self.click_notification_peek()

        def get_expanded_notification(notification_text: str) -> List[str]:
            # notification text looks like this "bla bla bla (X)" where X is a number
            count = int(notification_text[notification_text.rfind('(') + 1: -1])
            return [notification_text] * count

        peek_notifications = [get_expanded_notification(element.text) for
                              element in
                              self.driver.find_elements_by_css_selector(self.NOTIFICATION_PEEK_TITLE)]

        # flatten list
        peek_notifications = [
            item for sublist in peek_notifications for item in sublist]

        self.click_notification_peek()
        return peek_notifications

    def is_text_in_peek_notifications(self, text):
        return any(text in notification for notification in self.get_peek_notifications())

    def get_timestamps_in_peek_notifications(self):
        elements = self.driver.find_elements_by_css_selector(
            self.NOTIFICATION_PEEK_TIMESTAMP_CSS)
        return [element.text for element in elements]

    def get_rows_from_notification_table(self):
        rows = self.driver.find_elements_by_css_selector('tr.x-row.clickable')
        return [line.text for line in rows]

    @staticmethod
    def get_timestamps_from_rows(rows):
        return [line.split('\n')[0] for line in rows]

    @staticmethod
    def convert_timestamp_to_datetime(timestamp):
        # timestamp format: 2018-10-09 16:34:10
        return datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')

    def verify_amount_of_notifications(self, count: int):
        """
        Waits until the amount of notifications is the amount specified, or fails
        """
        wait_until(lambda: len(self.get_peek_notifications()) == count, total_timeout=60 * 5)
