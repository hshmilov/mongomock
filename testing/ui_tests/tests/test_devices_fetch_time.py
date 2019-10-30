from services.adapters.ad_service import AdService
from ui_tests.tests.test_entities_table import TestEntitiesTable


class TestDevicesFetchTime(TestEntitiesTable):
    def test_fetch_time(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row()
        fetch_time = self.devices_page.get_fetch_time()
        first_fetch_time = self.devices_page.get_first_fetch_time()
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row()
        new_fetch_time = self.devices_page.get_fetch_time()
        new_first_fetch_time = self.devices_page.get_first_fetch_time()
        # check if fetch_time was changed
        assert fetch_time != new_fetch_time
        # check if first_fetch_time remains the same
        assert first_fetch_time == new_first_fetch_time

    def test_fetch_time_restart_adapter(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row()
        fetch_time = self.devices_page.get_fetch_time()
        ad_service = AdService()
        ad_service.take_process_ownership()
        ad_service.stop()
        ad_service.start_and_wait()
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row()
        new_fetch_time = self.devices_page.get_fetch_time()
        # check if fetch_time was changed
        assert fetch_time != new_fetch_time

    def test_search_first_time_field(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()
        self.devices_page.select_query_field(self.devices_page.FIELD_FIRST_FETCH_TIME)
        self.devices_page.select_query_comp_op(self.devices_page.QUERY_COMP_EXISTS)
        self.devices_page.wait_for_spinner_to_end()
        self.devices_page.wait_for_table_to_load()
        assert self.devices_page.count_entities() > 0
