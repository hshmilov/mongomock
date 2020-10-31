import time
from datetime import datetime
from ui_tests.tests.ui_test_base import TestBase


class TestCustomHistoryScheduling(TestBase):

    DISCOVERY_HISTORY_PHASE_START_MESSAGE = 'Discovery phase \'Save History\' started'
    DISCOVERY_HISTORY_PHASE_END_MESSAGE = 'Discovery phase \'Save History\' ended'
    CUSTOM_HISTORY_PHASE_START_MESSAGE = 'Saving historical snapshot started'
    CUSTOM_HISTORY_PHASE_END_MESSAGE = 'Saving historical snapshot ended'

    def test_custom_history_scheduling_every_cycle(self):
        self.settings_page.switch_to_page()
        self.settings_page.save_daily_historical_snapshot()
        self.settings_page.set_history__to_every_cycle()
        self.base_page.run_discovery()

        audit_logs = self.audit_page.get_last_activity_logs_messages(num_of_logs=20)
        assert self.DISCOVERY_HISTORY_PHASE_START_MESSAGE in audit_logs
        assert self.DISCOVERY_HISTORY_PHASE_END_MESSAGE in audit_logs

    def test_custom_history_scheduling_every_x_days(self):
        self.settings_page.switch_to_page()
        self.settings_page.save_daily_historical_snapshot()

        # to start the job on round time
        time.sleep(60 - datetime.utcnow().second)
        self.settings_page.set_history__to_time_of_day(time_of_day=self.settings_page.set_discovery_time(minutes=1))

        # Just to make sure start & end history will make it.
        time.sleep(90)
        audit_logs = self.audit_page.get_last_activity_logs_messages(num_of_logs=20)
        assert self.CUSTOM_HISTORY_PHASE_START_MESSAGE in audit_logs
        assert self.CUSTOM_HISTORY_PHASE_END_MESSAGE in audit_logs

        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        audit_logs = self.audit_page.get_last_activity_logs_messages(num_of_logs=20)
        assert self.DISCOVERY_HISTORY_PHASE_START_MESSAGE not in audit_logs
        assert self.DISCOVERY_HISTORY_PHASE_END_MESSAGE not in audit_logs

    def test_custom_history_scheduling_weekdays(self):
        self.settings_page.switch_to_page()
        self.settings_page.save_daily_historical_snapshot()

        # to start the job on round time
        time.sleep(60 - datetime.utcnow().second)
        self.settings_page.set_history__to_weekdays(time_of_day=self.settings_page.set_discovery_time(minutes=1),
                                                    weekdays=[datetime.now().strftime('%A')])

        # Just to make sure start & end history will make it.
        time.sleep(90)
        audit_logs = self.audit_page.get_last_activity_logs_messages(num_of_logs=20)
        assert self.CUSTOM_HISTORY_PHASE_START_MESSAGE in audit_logs
        assert self.CUSTOM_HISTORY_PHASE_END_MESSAGE in audit_logs

        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        audit_logs = self.audit_page.get_last_activity_logs_messages(num_of_logs=20)
        assert self.DISCOVERY_HISTORY_PHASE_START_MESSAGE not in audit_logs
        assert self.DISCOVERY_HISTORY_PHASE_END_MESSAGE not in audit_logs
