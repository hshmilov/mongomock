# pylint: disable=R0915
import time

from flaky import flaky

from ui_tests.tests.ui_consts import JSON_ADAPTER_SEARCH, JSON_ADAPTER_NAME, JSON_ADAPTER_PLUGIN_NAME
from ui_tests.tests.ui_test_base import TestBase


class TestRealtime(TestBase):
    @flaky(max_runs=2)
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
        device_adapters = self.devices_page.get_column_data_adapter_names()
        assert any(JSON_ADAPTER_PLUGIN_NAME in x for x in device_adapters)

        # delete those devices
        self.axonius_system.get_devices_db().delete_many({})
        time.sleep(10)
        self.devices_page.switch_to_page()
        self.devices_page.refresh_table()

        # make sure they're gone
        device_adapters = self.devices_page.get_column_data_adapter_names()
        assert not any(JSON_ADAPTER_PLUGIN_NAME in x for x in device_adapters)

        # wait for a while to make sure that any potential RT cycle would've run
        time.sleep(40)

        # refresh to make sure
        self.devices_page.refresh_table()

        # make sure the adapter haven't brought them again
        device_adapters = self.devices_page.get_column_data_adapter_names()
        assert not any(JSON_ADAPTER_PLUGIN_NAME in x for x in device_adapters)

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

        device_adapters = self.devices_page.get_column_data_adapter_names()
        assert any(JSON_ADAPTER_PLUGIN_NAME in x for x in device_adapters)

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
        time.sleep(10)
        self.devices_page.switch_to_page()
        self.devices_page.refresh_table()

        # make sure they're gone
        device_adapters = self.devices_page.get_column_data_adapter_names()
        assert not any(JSON_ADAPTER_PLUGIN_NAME in x for x in device_adapters)

        # wait for a while to make sure that any potential RT cycle would've run
        time.sleep(40)

        # refresh to make sure
        self.devices_page.refresh_table()

        # make sure the adapter haven't brough them again
        device_adapters = self.devices_page.get_column_data_adapter_names()
        assert not any(JSON_ADAPTER_PLUGIN_NAME in x for x in device_adapters)
