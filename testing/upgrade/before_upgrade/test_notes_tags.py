from axonius.utils.wait import wait_until
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

        if self.devices_page.count_entities() > 1:
            self.devices_page.open_link_dialog()
            wait_until(lambda: 'You are about to link 2 devices.' in self.devices_page.read_delete_dialog())
            self.devices_page.confirm_link()
            wait_until(lambda: self.devices_page.count_entities() == 1)

        self.devices_page.toggle_select_all_rows_checkbox()
        self.devices_page.add_new_tags([Tags.tag_1])

    def select_device(self, device_name):
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.build_query(self.devices_page.FIELD_ASSET_NAME,
                                      device_name,
                                      self.devices_page.QUERY_COMP_EQUALS)
