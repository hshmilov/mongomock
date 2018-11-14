from ui_tests.tests import ui_consts
from ui_tests.tests.ui_test_base import TestBase
from axonius.entities import EntityType


class TestEntityNotes(TestBase):
    NOTE_1_TEXT = 'Cool Entity'
    NOTE_2_TEXT = 'Great Entity'
    COLUMN_NOTE = 'Note'

    def _create_notes_user(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()
        self.settings_page.create_new_user(ui_consts.NOTES_USERNAME, ui_consts.NEW_PASSWORD,
                                           ui_consts.FIRST_NAME, ui_consts.LAST_NAME)
        self.settings_page.wait_for_user_created_toaster()
        for entity_type in EntityType:
            self.settings_page.select_permissions(entity_type.name, self.settings_page.READ_WRITE_PERMISSION)
        self.settings_page.click_save_manage_users_settings()
        self.settings_page.wait_for_user_permissions_saved_toaster()

    def _execute_notes_basic_operations(self, entities_page):
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()
        entities_page.click_row()
        entities_page.click_notes_tab()
        entities_page.create_note(self.NOTE_1_TEXT)
        assert [self.NOTE_1_TEXT] == entities_page.get_column_data(self.COLUMN_NOTE)
        entities_page.edit_note(self.NOTE_2_TEXT)
        assert [self.NOTE_2_TEXT] == entities_page.get_column_data(self.COLUMN_NOTE)
        entities_page.remove_note()

    def _test_notes_basic_operations(self, entities_page):
        self._execute_notes_basic_operations(entities_page)
        self.login_page.switch_user(ui_consts.NOTES_USERNAME, ui_consts.NEW_PASSWORD)
        self._execute_notes_basic_operations(entities_page)
        self.login_page.switch_user(self.username, self.password)

    def _test_notes_permissions(self, entities_page):
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()
        entities_page.click_row()
        entities_page.click_notes_tab()
        entities_page.create_note(self.NOTE_1_TEXT)
        self.login_page.switch_user(ui_consts.NOTES_USERNAME, ui_consts.NEW_PASSWORD)
        entities_page.switch_to_page()
        entities_page.click_row()
        entities_page.click_notes_tab()
        entities_page.create_note(self.NOTE_2_TEXT)
        admins_note = entities_page.find_row_readonly()
        assert len(admins_note) == 1
        assert self.NOTE_1_TEXT in admins_note[0].text

    def test_notes_sanity(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self._create_notes_user()
        self._test_notes_basic_operations(self.users_page)
        self._test_notes_permissions(self.users_page)
        self._test_notes_basic_operations(self.devices_page)
        self._test_notes_permissions(self.devices_page)
