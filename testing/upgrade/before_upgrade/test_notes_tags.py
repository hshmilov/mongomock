from ui_tests.tests.ui_consts import Notes, Tags
from ui_tests.tests.ui_test_base import TestBase


class TestNotes(TestBase):
    def test_create_note(self):
        self.select_device(Notes.note1_device_filter)

        self.devices_page.click_row()
        self.devices_page.click_notes_tab()
        self.devices_page.create_note(Notes.note1_text)

    def test_create_tag(self):
        self.select_device(Notes.note1_device_filter)

        self.devices_page.select_all_page_rows_checkbox()
        self.devices_page.add_new_tag(Tags.tag_1)

    def select_device(self, device_name):
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.fill_filter(device_name)
        self.devices_page.enter_search()
        self.devices_page.wait_for_table_to_load()
