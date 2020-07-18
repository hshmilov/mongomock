import time
from copy import copy

from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import MANAGED_DEVICES_QUERY_NAME
from axonius.utils.wait import wait_until


class TestNotifications(TestBase):

    def test_notifications_sort_order(self):
        """
        Tests notification popup sort order by timestamp
        if the order is correct, the server will send the same list ( until new notification entered )
        Tests Issue: https://axonius.atlassian.net/browse/AX-7332
        """
        #  Creating new 'tag' enforcement.
        self.base_page.run_discovery()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.create_tag_enforcement(
            'Run Tag', MANAGED_DEVICES_QUERY_NAME, save=False)
        # Adding 10 Success actions for this test Enforcement
        for count in range(10):
            self.enforcements_page.add_push_notification(
                f'Special Push Action {count}!', self.enforcements_page.SUCCESS_ACTIONS_TEXT)

        # Simulate 15 clicks on 'run' button, to get more than 100 notifications.
        for _ in range(15):
            self.enforcements_page.click_run_button()
            self.enforcements_page.wait_for_task_in_progress_toaster()
            # we don't want to click too fast
            time.sleep(1)
        # Wait for all tasks to complete..
        # Should be 150 + wait_for_count, but we have an unrelated known bug
        wait_until(lambda: self.notification_page.wait_for_count_larger_than(140),
                   check_return_value=False,
                   tolerated_exceptions_list=[AssertionError])

        notification_times = self.notification_page.get_timestamps_list_from_peek_notifications()
        notifications_sorted = copy(notification_times)
        notifications_sorted.sort(reverse=True)
        assert notification_times == notifications_sorted

    def test_notifications_new_unseen_indicator(self):
        """
        Tests notification new unseen indicator (near the bell icon).
        The number if the indicator must be a positive number.
        Tests Issue: https://axonius.atlassian.net/browse/AX-7251
        """
        #  Creating new 'tag' enforcement.
        self.base_page.run_discovery()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.create_tag_enforcement(
            'Run Tag', MANAGED_DEVICES_QUERY_NAME, save=False)
        # Adding 10 Success actions for this test Enforcement
        for count in range(10):
            self.enforcements_page.add_push_notification(
                f'Special Push Action {count}!', self.enforcements_page.SUCCESS_ACTIONS_TEXT)

        # Simulate 15 clicks on 'run' button, to get more than 100 notifications.
        for _ in range(15):
            self.enforcements_page.click_run_button()
            self.enforcements_page.wait_for_task_in_progress_toaster()
            # we don't want to click too fast
            time.sleep(1)
        # Wait for all tasks to complete..
        # Should be 150 + wait_for_count, but we have an unrelated known bug
        wait_until(lambda: self.notification_page.wait_for_count_larger_than(140),
                   check_return_value=False,
                   tolerated_exceptions_list=[AssertionError])
        # Bug is reproduced when notifications-table is fully loaded over 100.
        self.notification_page.switch_to_page()
        self.notification_page.wait_for_table_to_be_responsive()
        # Trying to get negative notifications number, for each click.
        for _ in range(10):
            self.notification_page.click_notification_peek()
            assert self.notification_page.get_count() >= 0
