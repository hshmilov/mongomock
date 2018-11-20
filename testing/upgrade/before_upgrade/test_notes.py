from ui_tests.tests.ui_consts import Notes
from ui_tests.tests.ui_test_base import TestBase


class TestNotes(TestBase):
    def test_create_note(self):
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.fill_filter(Notes.note1_device_filter)
        self.devices_page.enter_search()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row()
        self.devices_page.click_notes_tab()
        self.devices_page.create_note(Notes.note1_text)
