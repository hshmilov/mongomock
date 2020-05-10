from copy import copy

from ui_tests.tests.ui_test_base import TestBase


class TestNotifications(TestBase):

    def test_notifications_sort_order(self):
        """
        Tests notification popup sort order by timestamp
        if the order is correct, the server will send the same list ( until new notification entered )
        Tests Issue: https://axonius.atlassian.net/browse/AX-7332
        """
        self.settings_page.set_notify_on_adapters_fetch()
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()

        notification_times = self.notification_page.get_timestamps_list_from_peek_notifications()
        notifications_sorted = copy(notification_times)
        notifications_sorted.sort(reverse=True)
        assert notification_times == notifications_sorted
