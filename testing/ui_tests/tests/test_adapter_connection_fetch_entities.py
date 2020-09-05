import pytest

from axonius.utils.wait import wait_until
from ui_tests.tests.ui_consts import AD_ADAPTER_NAME, ScheduleTriggers
from ui_tests.tests.ui_test_base import TestBase


class TestAdapterConnectionFetchEntities(TestBase):
    FETCH_STARTED_ACTION = 'Fetch Started'
    FETCH_ENDED_ACTION = 'Fetch Ended'

    def test_connection_without_fetch_custom_schedule(self):
        # this test must be the first test in the class,
        # since we depends on the first_fetch flag to be false (every connection have this flag),
        # to make the device fetch trigger after any save
        self.adapters_page.toggle_adapters_connection_discovery(AD_ADAPTER_NAME)
        self.adapters_page.toggle_adapter_client_connection_discovery(adapter_name=AD_ADAPTER_NAME,
                                                                      client_position=0,
                                                                      do_fetch=False,
                                                                      discovery_trigger=ScheduleTriggers.every_x_hours)
        self.adapters_page.wait_for_connection_saved_toaster_start()

        self.devices_page.switch_to_page()
        wait_until(self._check_for_devices_exist, total_timeout=240, interval=5)

        self._assert_last_audit_action_is_one_of([self.FETCH_STARTED_ACTION, self.FETCH_ENDED_ACTION])

        self.adapters_page.toggle_adapters_connection_discovery(AD_ADAPTER_NAME)

    def test_connection_and_fetch(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.open_add_edit_server(AD_ADAPTER_NAME, 1)
        self.adapters_page.click_save_and_fetch()
        self.adapters_page.wait_for_data_collection_toaster_start()

        self._assert_last_audit_action_is_one_of([self.FETCH_STARTED_ACTION])

        self.devices_page.switch_to_page()
        wait_until(self._check_for_devices_exist, total_timeout=240, interval=5)

    def test_connection_without_fetch(self):
        self.adapters_page.switch_to_page()
        self.adapters_page.open_add_edit_server(AD_ADAPTER_NAME, 1)
        self.adapters_page.click_save_without_fetch()
        self.adapters_page.wait_for_connection_saved_toaster_start()

        self._assert_last_audit_action_is_one_of([self.FETCH_STARTED_ACTION], False)

        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()
        with pytest.raises(TimeoutError):
            wait_until(self._check_for_devices_exist, total_timeout=240, interval=5)

    def _check_for_devices_exist(self):
        self.devices_page.hard_refresh()
        self.devices_page.wait_for_table_to_be_responsive()
        return self.devices_page.get_table_count() > 0

    def _assert_last_audit_action_is_one_of(self, texts: list, exist: bool = True):
        self.audit_page.switch_to_page()
        self.audit_page.wait_for_table_to_be_responsive()
        last_action = self.audit_page.get_last_activity_log_action()
        if exist:
            assert last_action in texts
        else:
            assert last_action not in texts
