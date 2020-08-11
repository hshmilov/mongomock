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

    def test_custom_discovery_time(self):
        try:
            self._prepare_clients()
            self.adapters_page.toggle_adapters_discovery_configurations(adapter_name=JSON_ADAPTER_NAME,
                                                                        discovery_time=2, discovery_interval=1)
            axonius_system = get_service()
            wait_until(
                lambda: axonius_system.scheduler.log_tester.is_str_in_log('Finished Custom Discovery cycle', 10),
                total_timeout=MAX_WAIT_TIME_FOR_CUSTOM_DISCOVERY)
        finally:
            self.adapters_page.toggle_adapters_discovery_configurations(adapter_name=JSON_ADAPTER_NAME)
            self.adapters_page.restore_json_client()

    @staticmethod
    def _get_client_last_fetch_time(client_id):
        json_service = JsonFileService()
        client = json_service.get_client_fetch_time(client_id)
        if client:
            return client[LAST_FETCH_TIME]
        return None

    @staticmethod
    def _get_adapter_last_fetch_time():
        json_service = JsonFileService()
        return json_service.get_plugin_settings_keyval()[LAST_FETCH_TIME]

    def test_custom_connection_discovery(self):
        try:
            self._prepare_clients()
            self.adapters_page.toggle_adapters_discovery_configurations(adapter_name=JSON_ADAPTER_NAME,
                                                                        discovery_time=2, discovery_interval=1)
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
            self.adapters_page.toggle_adapter_client_connection_discovery(adapter_name=JSON_ADAPTER_NAME,
                                                                          client_position=0,
                                                                          discovery_time=2,
                                                                          discovery_interval=1)
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
