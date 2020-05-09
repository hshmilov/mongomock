import time
from datetime import datetime, timedelta

import pytest
from selenium.common.exceptions import ElementNotInteractableException

from axonius.utils.wait import wait_until
from services.adapters import stresstest_service
from services.plugins.system_scheduler_service import DEAFULT_SYSTEM_RESEARCH_RATE_ATTRIB_NAME
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import STRESSTEST_ADAPTER_NAME


NEXT_CYCLE_START_IN = 'Next cycle starts in:'
LAST_CYCLE_COMPLETED_AT = 'Last cycle completed at:'
LAST_CYCLE_STARTED_AT = 'Last cycle started at:'


class TestDiscoverySchedule(TestBase):

    @staticmethod
    def set_discovery_time(minutes):
        current_utc = datetime.utcnow()
        timepicker_input = current_utc + timedelta(minutes=minutes)
        return timepicker_input.time().strftime('%I:%M%p').lower()

    def check_next_cycle_start_in_min(self, time_unit='minute', time_in_min=0):
        return self.check_next_cycle_start_in(time_unit, time_value=time_in_min)

    def check_next_cycle_start_in_hours(self, time_unit='hours', time_in_hours=0):
        return self.check_next_cycle_start_in(time_unit, time_value=time_in_hours)

    def check_next_cycle_start_in(self, time_unit, time_value=0):
        self.dashboard_page.switch_to_page()
        cycle_into = self.dashboard_page.get_lifecycle_card_info()
        return f'{time_value} {time_unit}' in cycle_into.get(NEXT_CYCLE_START_IN)

    def check_last_cycle_completed(self):
        self.dashboard_page.switch_to_page()
        cycle_into = self.dashboard_page.get_lifecycle_card_info()
        try:
            started = datetime.strptime(cycle_into.get(LAST_CYCLE_STARTED_AT), '%Y-%m-%d %H:%M:%S')
            completed = datetime.strptime(cycle_into.get(LAST_CYCLE_COMPLETED_AT), '%Y-%m-%d %H:%M:%S')
            return completed > started
        except Exception:
            return False

    # pylint: disable=W0108
    def test_update_discovery_scheduler_daily(self):
        stress = stresstest_service.StresstestService()
        with stress.contextmanager(take_ownership=True):
            self.adapters_page.wait_for_adapter(STRESSTEST_ADAPTER_NAME)
            device_dict = {'device_count': 10, 'name': 'testonius', 'fetch_device_interval': 5}
            self.adapters_page.add_server(device_dict, STRESSTEST_ADAPTER_NAME)
            self.adapters_page.wait_for_server_green()
            self.adapters_page.wait_for_data_collection_toaster_absent()
            # CLOCK SYNC TO START ON ROUND TIME
            time.sleep(60 - datetime.utcnow().second)
            self.settings_page.set_discovery__to_time_of_day(self.set_discovery_time(minutes=2))

            # before discovery
            wait_until(lambda: self.check_next_cycle_start_in_min(time_in_min=2),
                       total_timeout=60 * 3, interval=0.1)
            # discovery started , verify next cycle timestamp update
            wait_until(lambda: self.check_next_cycle_start_in_hours(time_in_hours=24),
                       total_timeout=60 * 5)

            self.base_page.wait_for_stop_research()
            self.base_page.wait_for_run_research()

            # now the discovery cycle completed verify completed timestamp
            wait_until(lambda: self.check_last_cycle_completed(),
                       total_timeout=60 * 5)

    def test_set_discovery_schedule_to_interval_base(self):
        self.settings_page.set_discovery__to_interval_value(interval=8)
        # let verify changes saved
        wait_until(lambda: self.check_next_cycle_start_in_hours(time_in_hours=8),
                   total_timeout=60 * 5, interval=0.1)

    def test_negative_discovery_schedule_time_of_day(self):
        self.settings_page.switch_to_page()
        self.settings_page.set_discovery__to_time_of_day('bad_value', negative_flow=True)
        assert self.settings_page.find_schedule_date_error()

    def test_negative_discovery_schedule_interval(self):
        self.settings_page.switch_to_page()
        self.settings_page.set_discovery__to_interval_value(negative_flow=True)
        self.settings_page.blur_on_element(DEAFULT_SYSTEM_RESEARCH_RATE_ATTRIB_NAME)
        assert self.settings_page.find_schedule_rate_error()

    def _test_lifecycle_next_scan_daily_scheduled(self):
        self.settings_page.switch_to_page()
        self.settings_page.set_discovery__to_time_of_day(self.set_discovery_time(minutes=1))
        # before discovery
        wait_until(lambda: self.check_next_cycle_start_in_min(time_in_min=1),
                   total_timeout=60 * 10, interval=0.1)
        # discovery started , verify next cycle timestamp update
        wait_until(lambda: self.check_next_cycle_start_in_hours(time_in_hours=24),
                   total_timeout=60 * 10)

    def _test_lifecycle_next_scan_interval_scheduled(self):
        interval_value = 0.1 / 6

        def verify_schedule_interval_update():
            self.driver.refresh()
            self.settings_page.wait_for_system_research_interval()
            return self.settings_page.get_schedule_rate_value() == str(interval_value)

        self.settings_page.switch_to_page()
        self.settings_page.set_discovery_mode_dropdown_to_interval()

        self.settings_page.save_system_interval_schedule_settings(interval_value)

        wait_until(verify_schedule_interval_update,
                   total_timeout=60 * 10, interval=0.1)

        wait_until(lambda: self.check_next_cycle_start_in_min(time_in_min=1),
                   total_timeout=60 * 10, interval=0.1)

    @pytest.mark.skip('AX-7081')
    def test_schedule_lifecycle_next_scan(self):
        self._test_lifecycle_next_scan_daily_scheduled()

        wait_until(lambda: self.check_last_cycle_completed(),
                   total_timeout=60 * 10)

        self._test_lifecycle_next_scan_interval_scheduled()

    def test_discovery_schedule_tooltips(self):
        self.settings_page.switch_to_page()
        self.settings_page.open_discovery_mode_options()
        wait_until(lambda: self.settings_page.find_discovery_mode_options() is not None,
                   tolerated_exceptions_list=[ElementNotInteractableException])
        options = self.settings_page.find_discovery_mode_options()
        for option in options:
            assert option.text == option.get_attribute('title')
