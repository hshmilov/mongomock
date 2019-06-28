from datetime import datetime, timedelta

from axonius.consts.metric_consts import Query
from axonius.utils.wait import wait_until
from axonius.plugin_base import EntityType
from ui_tests.tests.ui_test_base import TestBase


class TestHistory(TestBase):
    def test_users_history_sanity(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        day_to_user_count = self._create_history(EntityType.Users, self.users_page.FIELD_USERNAME_NAME)
        self.users_page.refresh()
        self.users_page.switch_to_page()
        tester = self.axonius_system.gui.log_tester
        for day in range(1, 30):
            self.users_page.fill_datepicker_date(datetime.now() - timedelta(day))
            self.users_page.wait_for_table_to_load()
            assert self.users_page.count_entities() == day_to_user_count[day - 1]
            for user_name in self.users_page.get_column_data(self.users_page.FIELD_USERNAME_TITLE):
                assert int(user_name.split(', ')[0].split(' ')[-1]) == day
            self.users_page.close_datepicker()
            self.users_page.clear_existing_date()
            wait_until(lambda: tester.is_metric_in_log(Query.QUERY_HISTORY, '.*'))

    def test_devices_history_sanity(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        day_to_device_count = self._create_history(EntityType.Devices, self.devices_page.FIELD_HOSTNAME_NAME)
        self.devices_page.refresh()
        self.devices_page.switch_to_page()
        tester = self.axonius_system.gui.log_tester
        for day in range(1, 30):
            self.devices_page.fill_datepicker_date(datetime.now() - timedelta(day))
            self.devices_page.close_datepicker()
            self.devices_page.wait_for_table_to_load()
            assert self.devices_page.count_entities() == day_to_device_count[day - 1]
            for host_name in self.users_page.get_column_data(self.devices_page.FIELD_HOSTNAME_TITLE):
                assert int(host_name.split(' ')[-1]) == day
            self.devices_page.clear_existing_date()
            wait_until(lambda: tester.is_metric_in_log(Query.QUERY_HISTORY, '.*'))
