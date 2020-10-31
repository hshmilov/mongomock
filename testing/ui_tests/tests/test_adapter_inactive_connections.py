import time

from services.adapters.csv_service import CsvService
from test_credentials.test_csv_credentials import USERS_CLIENT_FILES
from ui_tests.tests.ui_consts import AD_ADAPTER_NAME, CSV_NAME
from ui_tests.tests.ui_test_base import TestBase
from axonius.consts.plugin_consts import WEEKDAYS


class TestAdapterInactiveConnections(TestBase):

    def test_inactive_clients_in_discovery(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.open_add_edit_server(AD_ADAPTER_NAME, 1)
        self.adapters_page.toggle_active_connection(False)
        self.adapters_page.click_save_without_fetch()
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()
        # expected to see only the device from json adapter
        assert self.devices_page.get_table_count() == 1
        # revert
        self.adapters_page.open_add_edit_server(AD_ADAPTER_NAME, 1)
        self.adapters_page.toggle_active_connection(True)
        self.adapters_page.click_save_without_fetch()

    def test_inactive_clients_adapter_schedule(self):
        with CsvService().contextmanager(take_ownership=True):
            self._init_csv_clients()
            self.adapters_page.toggle_adapters_discovery_configurations(
                CSV_NAME,
                mode=self.adapters_page.SCHEDULE_WEEKDAYS_TEXT,
                value=self.adapters_page.set_discovery_time(2),
                weekdays=WEEKDAYS)
            # wait for the schedule to begin 2 minutes + 1 minutes for the system scheduler to pick the job
            time.sleep(180)
            self._assert_no_user_name_exist('ron')
            # revert
            self.adapters_page.toggle_adapters_discovery_configurations(CSV_NAME)
            self.adapters_page.clean_adapter_servers(CSV_NAME, True)

    def test_inactive_clients_client_schedule(self):
        with CsvService().contextmanager(take_ownership=True):
            self._init_csv_clients()
            self.adapters_page.toggle_adapters_connection_discovery(CSV_NAME)
            self.adapters_page.toggle_adapter_client_connection_discovery(
                adapter_name=CSV_NAME,
                client_position=0,
                mode=self.adapters_page.SCHEDULE_WEEKDAYS_TEXT,
                value=self.adapters_page.set_discovery_time(2),
                weekdays=WEEKDAYS)
            # wait for the schedule to begin 2 minutes + 1 minutes for the system scheduler to pick the job
            time.sleep(180)
            self._assert_no_user_name_exist('ron')
            # revert
            self.adapters_page.toggle_adapters_connection_discovery(CSV_NAME)
            self.adapters_page.clean_adapter_servers(CSV_NAME, True)

    def test_inactive_clients_after_adapter_restart(self):
        with CsvService().contextmanager(take_ownership=True) as csv_service:
            self._init_csv_clients()
            assert self.adapters_page.count_green_connections() == 2
            assert self.adapters_page.count_inactive_connections() == 1
            csv_service.stop(should_delete=False)
            csv_service.start_and_wait()
            self.adapters_page.switch_to_page()
            self.adapters_page.click_adapter(CSV_NAME)
            self.adapters_page.wait_for_table_to_be_responsive()
            assert self.adapters_page.count_green_connections() == 2
            assert self.adapters_page.count_inactive_connections() == 1
            self.adapters_page.clean_adapter_servers(CSV_NAME, True)

    def _init_csv_clients(self):
        for position, client in enumerate(USERS_CLIENT_FILES, start=1):
            self.adapters_page.upload_csv(list(client.keys())[0], client, is_user_file=True, save_and_fetch=False)
            self.adapters_page.wait_for_server_green(position)
        self.adapters_page.open_add_edit_server(CSV_NAME, 1)
        self.adapters_page.toggle_active_connection(False)
        self.adapters_page.click_save_without_fetch()

    def _assert_no_user_name_exist(self, name):
        self.users_page.switch_to_page()
        self.users_page.wait_for_table_to_be_responsive()
        self.users_page.fill_filter(name)
        self.users_page.enter_search()
        # expected to see 0 users
        assert self.devices_page.get_table_count() == 0
