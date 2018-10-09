from ui_tests.tests.ui_test_base import TestBase


class TestDevicesTable(TestBase):
    LABELS_TEXTBOX_TEXT = 'foobar'

    def test_devices_action_add_and_remove_tag(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.driver.get(self.driver.current_url)
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_first_row_checkbox()
        self.devices_page.add_new_tag(self.LABELS_TEXTBOX_TEXT)
        assert self.devices_page.get_first_tag_text() == self.LABELS_TEXTBOX_TEXT
        self.devices_page.remove_first_tag()
        assert self.devices_page.get_first_tag_text() == ''
