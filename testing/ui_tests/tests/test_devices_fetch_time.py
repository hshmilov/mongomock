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
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row()
        new_fetch_time = self.devices_page.get_fetch_time()
        assert fetch_time != new_fetch_time

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
        assert fetch_time != new_fetch_time
