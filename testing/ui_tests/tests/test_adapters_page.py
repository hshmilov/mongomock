import os
import json

from test_credentials.test_cisco_credentials import cisco_json_file_mock_credentials
from test_credentials.test_esx_credentials import esx_json_file_mock_devices
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import AD_ADAPTER_NAME, JSON_ADAPTER_NAME


def get_cortex_dir() -> str:
    """ Returns the relative path to cortex repo root directory """
    return os.path.relpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


class TestAdaptersPage(TestBase):
    def test_adapters_page_sanity(self):
        self.adapters_page.add_json_server(cisco_json_file_mock_credentials)
        self.adapters_page.add_json_server(esx_json_file_mock_devices)
        self.adapters_page.wait_for_spinner_to_end()
        self.base_page.wait_for_run_research()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_query_wizard()
        adapters_from_query_wizard = self.devices_page.get_query_adapters_list()
        self.devices_page.close_dropdown()
        assert adapters_from_query_wizard == sorted(adapters_from_query_wizard)
        self.devices_page.close_dropdown()
        self.devices_page.open_edit_columns()
        adapters_from_edit_columns = self.devices_page.get_edit_columns_adapters_list()
        assert adapters_from_edit_columns == sorted(adapters_from_edit_columns)
        assert adapters_from_edit_columns == adapters_from_query_wizard
        self.devices_page.close_dropdown()
        self.devices_page.close_edit_columns()
        self.adapters_page.switch_to_page()
        self.adapters_page.restore_json_client()

    def test_adapters_page_help_link(self):
        self.adapters_page.wait_for_adapter(AD_ADAPTER_NAME)
        self.adapters_page.click_adapter(AD_ADAPTER_NAME)
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.wait_for_table_to_load()
        self.adapters_page.click_new_server()

        assert self.adapters_page.find_help_link()
        self.adapters_page.click_help_link()
        # switch to th new tab
        self.adapters_page.driver.switch_to_window(self.adapters_page.driver.window_handles[1])

        assert self.adapters_page.current_url == self.plugin_meta['active_directory_adapter']['link']

    def test_adapters_page_no_help_link(self):
        self.adapters_page.wait_for_adapter(JSON_ADAPTER_NAME)
        self.adapters_page.click_adapter(JSON_ADAPTER_NAME)
        self.adapters_page.wait_for_spinner_to_end()
        self.adapters_page.wait_for_table_to_load()
        self.adapters_page.click_new_server()

        assert not self.plugin_meta['json_file_adapter']['link']
        assert not self.adapters_page.find_help_link()

    def test_adapters_page_total_number_of_adapter(self):
        self.adapters_page.switch_to_page()
        assert self.adapters_page.get_adapters_table_length() == \
            self.adapters_page.get_total_adapters_count_from_switch_label()

    @property
    def plugin_meta(self):
        plugin_meta_path = os.path.join(get_cortex_dir(), 'plugins/gui/frontend/src/constants/plugin_meta.json')
        with open(plugin_meta_path, encoding='utf-8') as plugin_meta_file:
            return json.load(plugin_meta_file)
