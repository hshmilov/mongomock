from datetime import datetime, timedelta
import time

from ui_tests.tests.ui_test_base import TestBase
from axonius.plugin_base import EntityType


class TestHistory(TestBase):
    def test_users_history_sanity(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        day_to_user_count = self._create_history(EntityType.Users, self.users_page.FIELD_USERNAME_NAME)
        self.users_page.switch_to_page()
        for day in range(1, 30):
            self.users_page.fill_showing_results(datetime.now() - timedelta(day))
            # Sleep through the time it takes the date picker to react to the filled date
            time.sleep(0.5)
            self.users_page.wait_for_table_to_load()
            assert self.users_page.count_entities() == day_to_user_count[day - 1]
            for user_name in self.users_page.get_column_data(self.users_page.FIELD_USERNAME_NAME):
                assert user_name.split(' ')[-1] == day
            self.users_page.close_showing_results()
            self.users_page.clear_showing_results()

    def test_devices_history_sanity(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        day_to_device_count = self._create_history(EntityType.Devices, self.devices_page.FIELD_HOSTNAME_NAME)
        self.devices_page.switch_to_page()
        for day in range(1, 30):
            self.devices_page.fill_showing_results(datetime.now() - timedelta(day))
            # Sleep through the time it takes the date picker to react to the filled date
            time.sleep(0.5)
            self.devices_page.wait_for_table_to_load()
            assert self.devices_page.count_entities() == day_to_device_count[day - 1]
            for host_name in self.users_page.get_column_data(self.devices_page.FIELD_HOSTNAME_NAME):
                assert host_name.split(' ')[-1] == day
            self.devices_page.close_showing_results()
            self.devices_page.clear_showing_results()
