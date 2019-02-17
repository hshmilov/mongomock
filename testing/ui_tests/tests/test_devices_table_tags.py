import time

from axonius.utils.wait import wait_until
from services.plugins.general_info_service import GeneralInfoService
from ui_tests.tests.test_entities_table import TestEntitiesTable


class TestDevicesTable(TestEntitiesTable):
    LABELS_TEXTBOX_TEXT = 'Connection Error'

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
            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            toggle = self.settings_page.find_execution_toggle()
            self.settings_page.click_toggle_button(toggle, make_yes=True)
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_load()
            wait_until(lambda: any(self.devices_page.get_column_data(
                self.devices_page.FIELD_TAGS)), total_timeout=60 * 5)
            self.settings_page.switch_to_page()
            self.devices_page.switch_to_page()
            self.devices_page.click_sort_column(self.devices_page.FIELD_TAGS)
            self.devices_page.wait_for_table_to_load()
            self.devices_page.click_row_checkbox()
            tag_to_remove = self.devices_page.get_first_tag_text()
            self.devices_page.remove_tag(tag_to_remove)
            assert tag_to_remove not in self.devices_page.get_first_row_tags()

    def test_add_same_tag_from_user_and_plugin(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.select_all_page_rows_checkbox()
        self.devices_page.add_new_tag(self.LABELS_TEXTBOX_TEXT, 20)
        with GeneralInfoService().contextmanager(take_ownership=True):
            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            toggle = self.settings_page.find_execution_toggle()
            self.settings_page.click_toggle_button(toggle, make_yes=True)
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            self.devices_page.wait_for_table_to_load()
            time.sleep(150)
            self.settings_page.switch_to_page()
            self.base_page.run_discovery()
            self.devices_page.switch_to_page()
            time.sleep(150)
            tags_list = self.devices_page.get_column_data('Tags')
            for tag in tags_list:
                # general info can remove tag if its not relevant so we are checking if
                # there is zero or one from the label we entered at the beginning of the test
                assert tag.count(self.LABELS_TEXTBOX_TEXT) < 2
