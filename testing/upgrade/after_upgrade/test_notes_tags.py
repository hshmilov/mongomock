from axonius.utils.wait import wait_until
from ui_tests.tests.ui_consts import Notes, Tags
from ui_tests.tests.ui_test_base import TestBase


class TestNotes(TestBase):
    def test_admin_note(self):
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.build_query(self.devices_page.FIELD_ASSET_NAME,
                                      Notes.note1_device_filter,
                                      self.devices_page.QUERY_COMP_EQUALS)
        self.devices_page.click_row()
        self.devices_page.click_notes_tab()
        self.devices_page.search_note(Notes.note1_text)
        self.devices_page.wait_for_table_to_load()

        wait_until(lambda: Notes.note1_text == self.devices_page.get_note_by_text(Notes.note1_text).text,
                   tolerated_exceptions_list=[Exception])

    def test_create_tag(self):
        self.devices_page.switch_to_page()
        self.devices_page.build_query(self.devices_page.FIELD_ASSET_NAME,
                                      Notes.note1_device_filter,
                                      self.devices_page.QUERY_COMP_EQUALS)

        wait_until(lambda: Tags.tag_1 in self.devices_page.get_first_row_tags(),
                   tolerated_exceptions_list=[Exception])
