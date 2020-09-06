from datetime import datetime
from axonius.utils.wait import wait_until
from axonius.consts.adapter_consts import LAST_FETCH_TIME
from services.axonius_service import get_service
from services.adapters.json_file_service import JsonFileService
from test_credentials.test_esx_credentials import esx_json_file_mock_devices
from test_credentials.json_file_credentials import CLIENT_ID as JSON_CLIENT_NAME
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import JSON_ADAPTER_NAME


MAX_WAIT_TIME_FOR_CUSTOM_DISCOVERY = 60 * 5


class TestCustomDiscoverySchedule(TestBase):

    def _prepare_clients(self):
        self.adapters_page.add_server(esx_json_file_mock_devices, JSON_ADAPTER_NAME)
        self.adapters_page.wait_for_server_green(2)

    @staticmethod
    def _get_client_last_fetch_time(client_id, last_fetch_time=None):
        json_service = JsonFileService()
        client = json_service.get_client_fetch_time(client_id)
        if client and client[LAST_FETCH_TIME]:
            if not last_fetch_time:
                return client[LAST_FETCH_TIME]
            if last_fetch_time and client[LAST_FETCH_TIME] != last_fetch_time:
                return client[LAST_FETCH_TIME]
        return None

    @staticmethod
    def _get_adapter_last_fetch_time(last_fetch_time=None):
        json_service = JsonFileService()
        adapter_fetch_time = json_service.get_plugin_settings_keyval()[LAST_FETCH_TIME]
        if last_fetch_time:
            if adapter_fetch_time and adapter_fetch_time != last_fetch_time:
                return adapter_fetch_time
            return None
        return adapter_fetch_time

    def test_custom_connection_discovery(self):
        try:
            self._prepare_clients()
            self.adapters_page.toggle_adapters_discovery_configurations(
                adapter_name=JSON_ADAPTER_NAME,
                mode=self.adapters_page.DISCOVERY_SCHEDULE_SCHEDULED_TEXT,
                value=self.adapters_page.set_discovery_time(2))
            axonius_system = get_service()
            wait_until(
                lambda: axonius_system.scheduler.log_tester.is_str_in_log('Finished Custom Discovery cycle', 10),
                total_timeout=MAX_WAIT_TIME_FOR_CUSTOM_DISCOVERY)
            wait_until(self._get_adapter_last_fetch_time, total_timeout=MAX_WAIT_TIME_FOR_CUSTOM_DISCOVERY,
                       interval=30)

            adapter_last_fetch_time = self._get_adapter_last_fetch_time()
            assert adapter_last_fetch_time
            minutes_passed = (datetime.utcnow() - adapter_last_fetch_time).seconds / 60

            assert minutes_passed < 2  # the interval is 90s, so just to be sure.

            # Next section, will assert that when custom connection is set, the adapter
            # will not be triggered and the last_fetch_time will not be updated.
            self.adapters_page.toggle_adapters_connection_discovery(adapter_name=JSON_ADAPTER_NAME)
            self.adapters_page.toggle_adapter_client_connection_discovery(
                adapter_name=JSON_ADAPTER_NAME,
                client_position=0,
                mode=self.adapters_page.DISCOVERY_SCHEDULE_SCHEDULED_TEXT,
                value=self.adapters_page.set_discovery_time(2))
            wait_until(
                lambda: self._get_client_last_fetch_time(JSON_CLIENT_NAME),
                total_timeout=MAX_WAIT_TIME_FOR_CUSTOM_DISCOVERY,
                interval=30)

            json_service = JsonFileService()
            adapter_fetch_time_after_job_triggered = json_service.get_plugin_settings_keyval()[LAST_FETCH_TIME]
            assert adapter_fetch_time_after_job_triggered == adapter_last_fetch_time
            client_fetch_time = self._get_client_last_fetch_time(JSON_CLIENT_NAME)
            assert client_fetch_time
            minutes_passed = (datetime.utcnow() - client_fetch_time).seconds / 60
            assert minutes_passed < 2  # the interval is 90s, so just to be sure.
        finally:
            self.adapters_page.toggle_adapters_discovery_configurations(adapter_name=JSON_ADAPTER_NAME,
                                                                        toggle_connection=True)
            self.adapters_page.restore_json_client()

    def test_custom_connection_discovery_every_some_hours(self):
        try:
            # Enable custom connection adapter, and set every x hours mode.
            self.adapters_page.toggle_adapters_connection_discovery(adapter_name=JSON_ADAPTER_NAME)
            self.adapters_page.toggle_adapter_client_connection_discovery(
                adapter_name=JSON_ADAPTER_NAME,
                client_position=0,
                mode=self.adapters_page.DISCOVERY_SCHEDULE_INTERVAL_TEXT,
                value=0.05)  # 0.05 hours is 3 minutes.

            # Client should be triggered twice - upon save, and after X hours passed.
            wait_until(
                lambda: self._get_client_last_fetch_time(JSON_CLIENT_NAME),
                total_timeout=MAX_WAIT_TIME_FOR_CUSTOM_DISCOVERY,
                interval=30)

            client_immediate_fetch_time = self._get_client_last_fetch_time(JSON_CLIENT_NAME)
            assert client_immediate_fetch_time
            seconds_passed = (datetime.utcnow() - client_immediate_fetch_time).seconds
            assert seconds_passed < 30  # after save & connect, JSON adapter should fetch immediately.

            wait_until(
                lambda: self._get_client_last_fetch_time(JSON_CLIENT_NAME, last_fetch_time=client_immediate_fetch_time),
                total_timeout=MAX_WAIT_TIME_FOR_CUSTOM_DISCOVERY,
                interval=30)

            # This fetch time is the actual custom connection discovery trigger.
            client_fetch_time = self._get_client_last_fetch_time(JSON_CLIENT_NAME)
            assert client_fetch_time
            minutes_passed = (client_fetch_time - client_immediate_fetch_time).seconds / 60
            assert minutes_passed > 3  # it was set to run every 3 minutes, so minimum 3, max 5 (as the interval
            # is 90 seconds - so it could run after 4.5 minutes from the last run).
        finally:
            self.adapters_page.toggle_adapters_connection_discovery(adapter_name=JSON_ADAPTER_NAME)
            self.adapters_page.restore_json_client()

    def test_custom_connection_discovery_weekdays(self):
        try:
            # Enable custom connection adapter, and set every x hours mode.
            self.adapters_page.toggle_adapters_connection_discovery(adapter_name=JSON_ADAPTER_NAME)
            self.adapters_page.toggle_adapter_client_connection_discovery(
                adapter_name=JSON_ADAPTER_NAME,
                client_position=0,
                mode=self.adapters_page.DISCOVERY_SCHEDULE_WEEKDAYS_TEXT,
                value=self.adapters_page.set_discovery_time(2),
                weekdays=[datetime.now().strftime('%A')])

            # Client should be triggered twice - upon save, and after 2 minutes passed.
            wait_until(
                lambda: self._get_client_last_fetch_time(JSON_CLIENT_NAME),
                total_timeout=MAX_WAIT_TIME_FOR_CUSTOM_DISCOVERY,
                interval=30)

            client_immediate_fetch_time = self._get_client_last_fetch_time(JSON_CLIENT_NAME)
            assert client_immediate_fetch_time
            seconds_passed = (datetime.utcnow() - client_immediate_fetch_time).seconds
            assert seconds_passed < 30  # after save & connect, JSON adapter should fetch immediately.

            wait_until(
                lambda: self._get_client_last_fetch_time(JSON_CLIENT_NAME, last_fetch_time=client_immediate_fetch_time),
                total_timeout=MAX_WAIT_TIME_FOR_CUSTOM_DISCOVERY,
                interval=30)

            # This fetch time is the actual custom connection discovery trigger.
            client_fetch_time = self._get_client_last_fetch_time(JSON_CLIENT_NAME)
            assert client_fetch_time
            minutes_passed = (client_fetch_time - client_immediate_fetch_time).seconds / 60
            assert minutes_passed > 2  # it was set to run in 2 minutes
        finally:
            self.adapters_page.toggle_adapters_connection_discovery(adapter_name=JSON_ADAPTER_NAME)
            self.adapters_page.restore_json_client()

    def test_connection_custom_discovery_multiple_clients(self):
        try:
            self._prepare_clients()
            start_time = datetime.utcnow()
            self.adapters_page.toggle_adapters_discovery_configurations(
                adapter_name=JSON_ADAPTER_NAME,
                mode=self.adapters_page.DISCOVERY_SCHEDULE_SCHEDULED_TEXT,
                value=self.adapters_page.set_discovery_time(2),
                toggle_connection=True)

            # Enable Connection Discovery
            self.adapters_page.toggle_adapter_client_connection_discovery(
                adapter_name=JSON_ADAPTER_NAME,
                client_position=0,
                mode=self.adapters_page.DISCOVERY_SCHEDULE_INTERVAL_TEXT,
                value=0.05)  # 0.05 hours is 3 minutes.

            axonius_system = get_service()
            client2_name = esx_json_file_mock_devices.get('file_name')

            # Getting clients fetch time right after saving.
            client_immediate_fetch_time = self._get_client_last_fetch_time(JSON_CLIENT_NAME)
            client2_fetch_time = self._get_client_last_fetch_time(client2_name)
            assert client_immediate_fetch_time
            assert client2_fetch_time  # Connection discovery is not set, so fetch time should be null.

            # Verify adapters fetch time
            wait_until(
                lambda: axonius_system.scheduler.log_tester.is_str_in_log('Finished Custom Discovery cycle', 10),
                total_timeout=MAX_WAIT_TIME_FOR_CUSTOM_DISCOVERY)
            wait_until(self._get_adapter_last_fetch_time, total_timeout=MAX_WAIT_TIME_FOR_CUSTOM_DISCOVERY,
                       interval=30)
            adapter_last_fetch_time = self._get_adapter_last_fetch_time()
            assert adapter_last_fetch_time
            current_time = datetime.utcnow()
            minutes_passed_from_start = (current_time - start_time).seconds / 60
            assert minutes_passed_from_start > 1  # adapter is set to run in 2 minutes. but when there is no fetch_time,
            # it will be triggered immediately, instead of 2 minutes, it could be 1 minutes and X seconds.
            minutes_passed_after_trigger = (current_time - adapter_last_fetch_time).seconds / 60
            assert minutes_passed_after_trigger < 2  # the interval is 90s, so just to be sure.

            # Verify client without connection was not triggered.
            assert client2_fetch_time == self._get_client_last_fetch_time(client2_name)

            # Verify client connection was triggered.
            wait_until(
                lambda: self._get_client_last_fetch_time(JSON_CLIENT_NAME, last_fetch_time=client_immediate_fetch_time),
                total_timeout=MAX_WAIT_TIME_FOR_CUSTOM_DISCOVERY,
                interval=30)

            # This fetch time is the actual custom connection discovery trigger.
            client_fetch_time = self._get_client_last_fetch_time(JSON_CLIENT_NAME)
            assert client_fetch_time
            minutes_passed = (client_fetch_time - client_immediate_fetch_time).seconds / 60
            assert minutes_passed > 3  # it was set to run in 3 minutes

            # Remove custom discovery for adapter and connection.
            self.adapters_page.toggle_adapters_discovery_configurations(adapter_name=JSON_ADAPTER_NAME,
                                                                        toggle_connection=True)
            start_time = datetime.utcnow()
            self.settings_page.switch_to_page()
            self.settings_page.set_discovery__to_time_of_day(self.adapters_page.set_discovery_time(2))
            wait_until(
                lambda: self._get_adapter_last_fetch_time(last_fetch_time=adapter_last_fetch_time),
                total_timeout=MAX_WAIT_TIME_FOR_CUSTOM_DISCOVERY,
                interval=30)
            adapter_last_fetch_time = self._get_adapter_last_fetch_time()
            assert adapter_last_fetch_time
            minutes_passed = (adapter_last_fetch_time - start_time).seconds / 60
            assert 1 < minutes_passed < 3  # Global discovery is set to run in 2 minutes, global discovery does not
            # consider seconds.

        finally:
            self.adapters_page.restore_json_client()
