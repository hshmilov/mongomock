from datetime import datetime, timedelta
from axonius.utils.wait import wait_until
from services.adapters import stresstest_service
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import STRESSTEST_ADAPTER_NAME


NEXT_CYCLE_START_IN = 'Next cycle starts in:'
LAST_CYCLE_COMPLETED_AT = 'Last cycle completed at:'
LAST_CYCLE_STARTED_AT = 'Last cycle started at:'


class TestDiscoveryScheduleByTimeOfDay(TestBase):

    @staticmethod
    def set_discovery_time(minutes):
        current_utc = datetime.utcnow()
        timepicker_input = current_utc + timedelta(minutes=minutes)
        timepicker_input = timepicker_input.time().strftime('%I:%M%p')
        return timepicker_input

    def get_lifecycle_card_info(self) -> dict:
        """
        {   'System Lifecycle': 'STABLE',
            'Last cycle started at:': '2020-02-05 16:05:00',
            'Last cycle completed at:': '2020-02-05 16:05:13',
            'Next cycle starts in:': '24 hours'
        }
        :return: dict
        """
        sl_card = self.dashboard_page.find_system_lifecycle_card()
        assert self.dashboard_page.get_title_from_card(sl_card) == self.dashboard_page.SYSTEM_LIFECYCLE
        lst = sl_card.text.split('\n')

        return {lst[i].lstrip(): lst[i + 1]
                for i in range(0, len(lst))
                if i < lst.__len__() and
                lst[i].lstrip().startswith(('System', 'Last', 'Next')) and not
                lst[i + 1].lstrip().startswith(('System', 'Last', 'Next'))}

    def check_next_cycle_start_in_min(self, time_unit='minute', time_in_min=0):
        return self.check_next_cycle_start_in(time_unit, time_value=time_in_min)

    def check_next_cycle_start_in_hours(self, time_unit='hours', time_in_hours=0):
        return self.check_next_cycle_start_in(time_unit, time_value=time_in_hours)

    def check_next_cycle_start_in(self, time_unit, time_value=0):
        self.dashboard_page.switch_to_page()
        cycle_into = self.get_lifecycle_card_info()
        return f'{time_value} {time_unit}' in cycle_into.get(NEXT_CYCLE_START_IN)

    def check_last_cycle_completed(self):
        self.dashboard_page.switch_to_page()
        cycle_into = self.get_lifecycle_card_info()
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
            device_dict = {'device_count': 10, 'name': 'testonius', 'fetch_device_interval': 0}
            self.adapters_page.add_server(device_dict, STRESSTEST_ADAPTER_NAME)
            self.adapters_page.wait_for_server_green()

            self.settings_page.set_discovery__to_time_of_day(self.set_discovery_time(minutes=1))

            # before discovery
            wait_until(lambda: self.check_next_cycle_start_in_min(time_in_min=1),
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
        assert self.settings_page.find_schedule_rate_error()
