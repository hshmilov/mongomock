from flaky import flaky

from ui_tests.tests.ui_test_base import TestBase


class TestDevicesTable(TestBase):
    LABELS_TEXTBOX_TEXT = 'foobar'

    @flaky(max_runs=2)
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

    def test_device_save_query(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()

        self.devices_page.customize_view_and_save('test_save_query', 50, self.devices_page.FIELD_HOST_NAME,
                                                  [self.devices_page.FIELD_LAST_SEEN, self.devices_page.FIELD_OS_TYPE],
                                                  self.devices_page.JSON_ADAPTER_FILTER)
        view_data = self.devices_page.get_all_data()

        # Load some default view, to change it and test the saved view's influence
        self.devices_page.execute_saved_query('Windows Operating System')
        assert self.devices_page.get_all_data() != view_data

        self.devices_page.clear_filter()
        self.devices_page.execute_saved_query('test_save_query')

        # Check loaded data is equal to original one whose view was saved
        assert self.devices_page.get_all_data() == view_data
