import time
from datetime import datetime, timedelta
from axonius.utils.wait import wait_until
from services.axonius_service import get_service
from test_credentials.test_esx_credentials import esx_json_file_mock_devices
from ui_tests.pages.adapters_page import JSON_NAME
from ui_tests.tests.ui_test_base import TestBase


MAX_WAIT_TIME_FOR_CUSTOM_DISCOVERY = 60 * 5


class TestCustomDiscoverySchedule(TestBase):
    @staticmethod
    def set_discovery_time(minutes):
        current_utc = datetime.utcnow()
        timepicker_input = current_utc + timedelta(minutes=minutes)
        return timepicker_input.time().strftime('%I:%M%p').lower()

    def test_custom_discovery_time(self):
        try:
            self.adapters_page.add_server(esx_json_file_mock_devices, JSON_NAME)
            self.adapters_page.wait_for_server_green(2)

            self.adapters_page.click_advanced_settings()
            time.sleep(1.5)
            self.adapters_page.click_discovery_configuration()
            self.adapters_page.check_custom_discovery_schedule()
            self.adapters_page.fill_schedule_date(self.set_discovery_time(2))
            self.adapters_page.change_custom_discovery_interval(1)
            self.adapters_page.save_advanced_settings()
            axonius_system = get_service()
            wait_until(
                lambda: axonius_system.scheduler.log_tester.is_str_in_log('Finished Custom Discovery cycle', 10),
                total_timeout=MAX_WAIT_TIME_FOR_CUSTOM_DISCOVERY)
        finally:
            self.adapters_page.restore_json_client()
