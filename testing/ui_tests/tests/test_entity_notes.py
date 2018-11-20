from ui_tests.tests import ui_consts
from ui_tests.tests.ui_consts import NOTE_COLUMN
from ui_tests.tests.ui_test_base import TestBase
from axonius.entities import EntityType


class TestEntityNotes(TestBase):
    NOTE_1_TEXT = 'Cool Entity'
    NOTE_2_TEXT = 'Great Entity'
    NOTE_3_TEXT = 'Amazing Entity'
    COLUMN_NOTE = NOTE_COLUMN

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
        entities_page.load_notes()
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
        entities_page.load_notes()
        entities_page.create_note(self.NOTE_1_TEXT)
        self.login_page.switch_user(ui_consts.NOTES_USERNAME, ui_consts.NEW_PASSWORD)
        entities_page.load_notes()
        entities_page.create_note(self.NOTE_2_TEXT)
        admins_note = entities_page.find_row_readonly()
        assert len(admins_note) == 1
        assert self.NOTE_1_TEXT in admins_note[0].text
        self.login_page.switch_user(self.username, self.password)
        entities_page.load_notes()
        edited_note = f'Now my {self.NOTE_2_TEXT}!!!'
        entities_page.edit_note(edited_note)
        assert edited_note in entities_page.get_column_data(self.COLUMN_NOTE)
        self.login_page.switch_user(ui_consts.NOTES_USERNAME, ui_consts.NEW_PASSWORD)
        entities_page.load_notes()
        assert len(entities_page.find_row_readonly()) == 2
        self.login_page.switch_user(self.username, self.password)
        entities_page.load_notes()
        entities_page.remove_note()
        entities_page.remove_note()

    def _test_notes_search(self, entities_page):
        entities_page.load_notes()
        entities_page.create_note(self.NOTE_1_TEXT)
        entities_page.search_note(self.NOTE_1_TEXT[6:])
        assert [self.NOTE_1_TEXT] == entities_page.get_column_data(self.COLUMN_NOTE)
        entities_page.search_note(self.username)
        assert [self.NOTE_1_TEXT] == entities_page.get_column_data(self.COLUMN_NOTE)
        entities_page.search_note(ui_consts.NOTES_USERNAME)
        assert not len(entities_page.get_all_data())
        entities_page.search_note('This text should not be in table')
        assert not len(entities_page.get_all_data())
        entities_page.search_note('')
        entities_page.remove_note()

    def _test_notes_sort(self, entities_page):
        entities_page.load_notes()
        entities_page.create_note(self.NOTE_1_TEXT)
        entities_page.create_note(self.NOTE_2_TEXT)
        self.login_page.switch_user(ui_consts.NOTES_USERNAME, ui_consts.NEW_PASSWORD)
        entities_page.load_notes()
        entities_page.create_note(self.NOTE_3_TEXT)
        self.login_page.switch_user(self.username, self.password)
        entities_page.load_notes()
        entities_page.click_sort_column(self.COLUMN_NOTE)
        assert [self.NOTE_3_TEXT, self.NOTE_1_TEXT, self.NOTE_2_TEXT] == entities_page.get_column_data(self.COLUMN_NOTE)
        entities_page.click_sort_column(self.COLUMN_NOTE)
        assert [self.NOTE_2_TEXT, self.NOTE_1_TEXT, self.NOTE_3_TEXT] == entities_page.get_column_data(self.COLUMN_NOTE)
        entities_page.remove_note()
        entities_page.remove_note()
        entities_page.remove_note()

    def test_notes_sanity(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self._create_notes_user()
        self._test_notes_basic_operations(self.users_page)
        self._test_notes_permissions(self.users_page)
        self._test_notes_search(self.users_page)
        self._test_notes_sort(self.users_page)
        self._test_notes_basic_operations(self.devices_page)
        self._test_notes_permissions(self.devices_page)
        self._test_notes_search(self.devices_page)
        self._test_notes_sort(self.devices_page)
