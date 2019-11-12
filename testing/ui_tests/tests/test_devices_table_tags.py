from axonius.utils.wait import wait_until
from services.plugins.general_info_service import GeneralInfoService
from ui_tests.tests.test_entities_table import TestEntitiesTable


class TestDevicesTable(TestEntitiesTable):
    LABELS_TEXTBOX_TEXT = 'Connection Error'
    ALL_TAG_TEST = 'all tag test'

    def test_devices_action_add_and_remove_tag(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row_checkbox()
        self.devices_page.add_new_tag(self.LABELS_TEXTBOX_TEXT)
        assert self.LABELS_TEXTBOX_TEXT in self.devices_page.get_first_row_tags()
        self.devices_page.remove_first_tag()
        assert not self.devices_page.get_first_row_tags()

    def test_devices_action_remove_plugin_tag(self):
        with GeneralInfoService().contextmanager(take_ownership=True):
            self.enforcements_page.create_run_wmi_scan_on_each_cycle_enforcement()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_load()
            wait_until(lambda: any(self.devices_page.get_column_data_slicer(
                self.devices_page.FIELD_TAGS)), total_timeout=60 * 5)
            self.settings_page.switch_to_page()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_spinner_to_end()
            self.devices_page.click_sort_column(self.devices_page.FIELD_TAGS)
            self.devices_page.wait_for_table_to_load()
            self.devices_page.click_row_checkbox()
            tag_to_remove = self.devices_page.get_first_tag_text()
            self.devices_page.remove_tag(tag_to_remove)
            assert tag_to_remove not in self.devices_page.get_first_row_tags()

    def test_devices_action_add_tag_all_with_filter(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.execute_saved_query(self.devices_page.VALUE_SAVED_QUERY_WINDOWS)
        self.devices_page.select_all_current_page_rows_checkbox()
        self.devices_page.click_select_all_entities()
        self.devices_page.add_new_tag(self.ALL_TAG_TEST, self.devices_page.get_table_count())
        assert self.ALL_TAG_TEST in self.devices_page.get_first_row_tags()
        self.devices_page.reset_query()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.run_filter_query(self.devices_page.SPECIFIC_JSON_ADAPTER_FILTER)
        assert self.ALL_TAG_TEST not in self.devices_page.get_first_row_tags()
