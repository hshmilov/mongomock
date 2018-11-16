#pylint: disable=R0915
import time

from ui_tests.tests.test_adapters import JSON_ADAPTER_SEARCH, JSON_ADAPTER_NAME, JSON_ADAPTER_PLUGIN_NAME
from ui_tests.tests.ui_test_base import TestBase


class TestDiscovery(TestBase):
    def test_stop_discovery(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery(wait=False)
        self.base_page.stop_discovery()

    def test_stop_discovery_after_full_cycle(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.base_page.run_discovery(wait=False)
        self.base_page.stop_discovery()

    def test_realtime(self):
        """
        Test that the adapter is not an RT adapter by waiting for device to appear without cycle, and
        asserting no devices have appeared.
        Then makes that adapter an RT adapter and waits for devices to appear, asserting they will.
        Then makes that adapter a non-RT adapter again, and again verifies that devices don't reappear.
        """
        # make sure there's an adapter
        self.settings_page.switch_to_page()
        self.base_page.run_discovery(wait=True)
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.search(JSON_ADAPTER_SEARCH)
        adapter_list = self.adapters_page.get_adapter_list()
        assert len(adapter_list) == 1
        assert adapter_list[0].name == JSON_ADAPTER_NAME

        # make sure it brought some devices
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        all_devices = self.devices_page.get_all_data_proper()
        assert any(JSON_ADAPTER_PLUGIN_NAME in x['Adapters'] for x in all_devices)

        # delete those devices
        self.axonius_system.get_devices_db().delete_many({})
        self.axonius_system.aggregator.rebuild_views()
        time.sleep(10)
        self.devices_page.switch_to_page()
        self.devices_page.refresh_table()

        # make sure they're gone
        all_devices = self.devices_page.get_all_data_proper()
        assert not any(JSON_ADAPTER_PLUGIN_NAME in x['Adapters'] for x in all_devices)

        # wait for a while to make sure that any potential RT cycle would've run
        time.sleep(40)

        # refresh to make sure
        self.devices_page.refresh_table()

        # make sure the adapter haven't brough them again
        all_devices = self.devices_page.get_all_data_proper()
        assert not any(JSON_ADAPTER_PLUGIN_NAME in x['Adapters'] for x in all_devices)

        # make the adapter a RT adapter
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.click_adapter(JSON_ADAPTER_NAME)
        self.adapters_page.click_advanced_settings()
        time.sleep(1.5)  # wait because of the open window animation
        self.adapters_page.check_rt_adapter()
        self.adapters_page.save_advanced_settings()

        # wait for a while to make sure the RT cycle ran
        time.sleep(40)

        # verify the adapter has brought the device by the RT cycle
        self.devices_page.switch_to_page()
        self.devices_page.refresh_table()

        all_devices = self.devices_page.get_all_data_proper()
        assert any(JSON_ADAPTER_PLUGIN_NAME in x['Adapters'] for x in all_devices)

        # make the adapter a non-RT adapter, again
        self.adapters_page.switch_to_page()
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.click_adapter(JSON_ADAPTER_NAME)
        self.adapters_page.click_advanced_settings()
        time.sleep(1.5)  # wait because of the open window animation
        self.adapters_page.check_rt_adapter()
        self.adapters_page.save_advanced_settings()

        # now we're testing that the adapter can become a non-RT again and stop fetching
        # delete the devices brought,
        self.axonius_system.get_devices_db().delete_many({})
        self.axonius_system.aggregator.rebuild_views()
        time.sleep(10)
        self.devices_page.switch_to_page()
        self.devices_page.refresh_table()

        # make sure they're gone
        all_devices = self.devices_page.get_all_data_proper()
        assert not any(JSON_ADAPTER_PLUGIN_NAME in x['Adapters'] for x in all_devices)

        # wait for a while to make sure that any potential RT cycle would've run
        time.sleep(40)

        # refresh to make sure
        self.devices_page.refresh_table()

        # make sure the adapter haven't brough them again
        all_devices = self.devices_page.get_all_data_proper()
        assert not any(JSON_ADAPTER_PLUGIN_NAME in x['Adapters'] for x in all_devices)
