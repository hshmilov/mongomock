from datetime import datetime, timedelta
import time

from ui_tests.tests import ui_consts
from ui_tests.tests.ui_consts import NOTE_COLUMN
from ui_tests.tests.ui_test_base import TestBase
from axonius.entities import EntityType


class TestEntityNotes(TestBase):
    NOTE_1_TEXT = 'Cool Entity'
    NOTE_2_TEXT = 'Great Entity'
    NOTE_3_TEXT = 'Amazing Entity'

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
        assert [self.NOTE_1_TEXT] == entities_page.get_column_data(NOTE_COLUMN)
        entities_page.edit_note(self.NOTE_2_TEXT)
        assert [self.NOTE_2_TEXT] == entities_page.get_column_data(NOTE_COLUMN)
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
        assert edited_note in entities_page.get_column_data(NOTE_COLUMN)
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
        assert [self.NOTE_1_TEXT] == entities_page.get_column_data(NOTE_COLUMN)
        entities_page.search_note(self.username)
        assert [self.NOTE_1_TEXT] == entities_page.get_column_data(NOTE_COLUMN)
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
        entities_page.click_sort_column(NOTE_COLUMN)
        assert [self.NOTE_3_TEXT, self.NOTE_1_TEXT, self.NOTE_2_TEXT] == entities_page.get_column_data(NOTE_COLUMN)
        entities_page.click_sort_column(NOTE_COLUMN)
        assert [self.NOTE_2_TEXT, self.NOTE_1_TEXT, self.NOTE_3_TEXT] == entities_page.get_column_data(NOTE_COLUMN)
        entities_page.remove_note()
        entities_page.remove_note()
        entities_page.remove_note()

    def _test_notes_historical(self, entities_page, entity_type: EntityType):
        entities_page.load_notes(entities_page.JSON_ADAPTER_FILTER)
        entities_page.create_note(self.NOTE_1_TEXT)
        self._update_and_create_history(entity_type)

        # Edit the original note in the current table
        entities_page.load_notes(entities_page.JSON_ADAPTER_FILTER)
        entities_page.edit_note(self.NOTE_2_TEXT)
        entities_page.switch_to_page()

        # Check no historical note was affected by the edit
        for day in range(1, 30):
            entities_page.fill_showing_results(datetime.now() - timedelta(day))
            # Sleep through the time it takes the date picker to react to the filled date
            time.sleep(0.5)
            entities_page.wait_for_table_to_load()
            entities_page.close_showing_results()
            if entities_page.get_all_data():
                entities_page.click_row()
                entities_page.click_notes_tab()
                assert [self.NOTE_1_TEXT] == entities_page.get_column_data(NOTE_COLUMN)
                entities_page.switch_to_page()
            entities_page.clear_showing_results()

        entities_page.close_showing_results()
        # Check the original note actually has the edited value
        entities_page.wait_for_table_to_load()
        entities_page.click_row()
        entities_page.click_notes_tab()
        assert [self.NOTE_2_TEXT] == entities_page.get_column_data(NOTE_COLUMN)

    def test_notes_sanity(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self._create_notes_user()
        self._test_notes_basic_operations(self.users_page)
        self._test_notes_permissions(self.users_page)
        self._test_notes_search(self.users_page)
        self._test_notes_sort(self.users_page)
        self._test_notes_historical(self.users_page, EntityType.Users)

        self._test_notes_basic_operations(self.devices_page)
        self._test_notes_permissions(self.devices_page)
        self._test_notes_search(self.devices_page)
        self._test_notes_sort(self.devices_page)
        self._test_notes_historical(self.devices_page, EntityType.Devices)

    # pylint: disable=anomalous-backslash-in-string
    def test_long_note(self):
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.load_notes()
        long_text = 'a' * 256
        self.devices_page.create_note(long_text)
        note_box = self.devices_page.get_note_by_text(long_text)
        user_box = self.devices_page.get_note_by_text('internal\/admin')
        assert note_box.rect['x'] + note_box.rect['width'] < user_box.rect['x']
