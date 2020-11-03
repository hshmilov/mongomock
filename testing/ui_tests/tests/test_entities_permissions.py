import pytest

from selenium.common.exceptions import TimeoutException, NoSuchElementException

from ui_tests.tests import ui_consts
from ui_tests.tests.entities_enforcements_tasks_test_base import EntitiesEnforcementTasksTestBase

# pylint: disable=no-member
from ui_tests.tests.ui_consts import JSON_ADAPTER_FILTER


class TestEntitiesPermissions(EntitiesEnforcementTasksTestBase):
    NOTE_TEXT = 'note text'
    TAG_NAME = 'test tag'

    CUSTOM_DEVICES_QUERY_SAVE_NAME = 'custom devices query'
    CUSTOM_DEVICES_NEW_QUERY_SAVE_NAME = 'custom new devices query'
    CUSTOM_USERS_QUERY_SAVE_NAME = 'custom users query'
    CUSTOM_NEW_USERS_SAVE_NAME = 'custom new users query'

    RUN_TAG_ENFORCEMENT_NAME = 'Run Tag'

    DUMMY_ENFORCEMENT_NAME = 'Dummy Enforcement'
    DUMMY_ACTION_NAME = 'Dummy Action Name'
    DUMMY_TAG_NAME = 'Dummy Tag Name'

    def test_devices_permissions(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        self.devices_page.switch_to_page()
        self.devices_page.run_filter_and_save(self.CUSTOM_DEVICES_QUERY_SAVE_NAME,
                                              JSON_ADAPTER_FILTER)
        self.devices_page.refresh()
        self.devices_page.load_notes()
        self.devices_page.create_note(self.NOTE_TEXT)
        self.devices_page.click_tab(self.devices_page.FIELD_TAGS)
        self.devices_page.open_edit_tags()
        self.devices_page.create_save_tags([self.TAG_NAME])
        self.devices_page.wait_for_spinner_to_end()

        self.settings_page.switch_to_page()
        settings_permissions = {
            'devices_assets': [
                'View devices'
            ],
            'enforcements': [
                'View Enforcement Center'
            ]
        }
        self._test_entities_with_only_view_permission(settings_permissions, user_role, self.devices_page,
                                                      self.devices_page.FIELD_NETWORK_INTERFACES)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'devices_assets',
                                                     'Edit devices',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self._test_entities_with_edit_permission(self.devices_page)

        self._test_run_enforcement_permission(self.devices_page, settings_permissions, user_role)

    def test_devices_saved_queries(self):
        self.devices_page.switch_to_page()
        self.base_page.run_discovery()
        self.create_tag_enforcement_run_it_return_entity_count()
        enforcement_set_id = self._find_enforcement_task_id()

        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        self.devices_page.switch_to_page()
        self.devices_page.run_filter_and_save(self.CUSTOM_DEVICES_QUERY_SAVE_NAME,
                                              JSON_ADAPTER_FILTER)
        self.settings_page.switch_to_page()
        settings_permissions = {
            'devices_assets': [
                'View devices'
            ],
            'enforcements': [
                'View Enforcement Center',
                'Edit Enforcement',
            ]
        }
        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.switch_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)

        self._test_saved_queries_without_any_permission(self.devices_page,
                                                        self.devices_queries_page,
                                                        self.CUSTOM_DEVICES_QUERY_SAVE_NAME)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'devices_assets',
                                                     'Run saved queries',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_saved_queries_with_run_permission(self.devices_page,
                                                     self.devices_queries_page,
                                                     self.CUSTOM_DEVICES_QUERY_SAVE_NAME)

        self._test_enforcements_without_view_tasks_permissions(enforcement_set_id)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'enforcements',
                                                     'View Enforcement Tasks',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_enforcements_with_view_tasks_permissions(enforcement_set_id)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'devices_assets',
                                                     'Edit saved queries',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_saved_queries_with_edit_permission(self.devices_page,
                                                      self.devices_queries_page,
                                                      self.CUSTOM_DEVICES_QUERY_SAVE_NAME)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'devices_assets',
                                                     'Create saved query',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_saved_queries_with_create_permission(self.devices_page, self.CUSTOM_DEVICES_NEW_QUERY_SAVE_NAME)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'enforcements',
                                                     'Add Enforcement',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_saved_queries_with_add_enforcement(self.devices_page, self.devices_queries_page,
                                                      self.CUSTOM_DEVICES_NEW_QUERY_SAVE_NAME)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'devices_assets',
                                                     'Delete saved query',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_saved_queries_with_delete_permission(self.devices_page,
                                                        self.devices_queries_page,
                                                        self.CUSTOM_DEVICES_QUERY_SAVE_NAME,
                                                        self.CUSTOM_DEVICES_NEW_QUERY_SAVE_NAME)

    def test_users_permissions(self):
        self.users_page.switch_to_page()
        self.base_page.run_discovery()
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)

        self.users_page.switch_to_page()
        self.users_page.refresh()
        self.users_page.load_notes()
        self.users_page.create_note(self.NOTE_TEXT)
        self.users_page.click_tab(self.devices_page.FIELD_TAGS)
        self.users_page.open_edit_tags()
        self.users_page.create_save_tags([self.TAG_NAME])
        self.users_page.wait_for_spinner_to_end()

        self.settings_page.switch_to_page()
        settings_permissions = {
            'users_assets': [
                'View users'
            ],
            'enforcements': [
                'View Enforcement Center'
            ]
        }
        self._test_entities_with_only_view_permission(settings_permissions, user_role, self.users_page)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'users_assets',
                                                     'Edit users',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self._test_entities_with_edit_permission(self.users_page)

    def test_users_saved_queries(self):
        self.users_page.switch_to_page()
        self.base_page.run_discovery()
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_users_settings()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)
        self.users_page.switch_to_page()
        self.users_page.run_filter_and_save(self.CUSTOM_USERS_QUERY_SAVE_NAME,
                                            JSON_ADAPTER_FILTER)

        self.settings_page.switch_to_page()
        settings_permissions = {
            'users_assets': [
                'View users'
            ],
            'enforcements': [
                'View Enforcement Center',
                'Edit Enforcement',
            ]
        }

        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.switch_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)

        self._test_saved_queries_without_any_permission(self.users_page,
                                                        self.users_queries_page,
                                                        self.CUSTOM_USERS_QUERY_SAVE_NAME)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'users_assets',
                                                     'Run saved queries',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_saved_queries_with_run_permission(self.users_page,
                                                     self.users_queries_page,
                                                     self.CUSTOM_USERS_QUERY_SAVE_NAME)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'users_assets',
                                                     'Edit saved queries',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_saved_queries_with_edit_permission(self.users_page,
                                                      self.users_queries_page,
                                                      self.CUSTOM_USERS_QUERY_SAVE_NAME)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'users_assets',
                                                     'Create saved query',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_saved_queries_with_create_permission(self.users_page, self.CUSTOM_NEW_USERS_SAVE_NAME)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'enforcements',
                                                     'Add Enforcement',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_saved_queries_with_add_enforcement(self.users_page, self.users_queries_page,
                                                      self.CUSTOM_NEW_USERS_SAVE_NAME)

        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'users_assets',
                                                     'Delete saved query',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)

        self._test_saved_queries_with_delete_permission(self.users_page,
                                                        self.users_queries_page,
                                                        self.CUSTOM_USERS_QUERY_SAVE_NAME,
                                                        self.CUSTOM_NEW_USERS_SAVE_NAME)

    def _test_entities_with_only_view_permission(self, settings_permissions, user_role, entities_page,
                                                 table_field=None):
        self.settings_page.update_role(user_role, settings_permissions, True)
        self.login_page.switch_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()
        assert entities_page.is_row_checkbox_absent()
        assert entities_page.is_actions_button_disable()
        entities_page.load_notes()
        entities_page.assert_add_note_disabled()
        assert not entities_page.can_edit_notes()
        assert entities_page.is_row_checkbox_absent()
        entities_page.click_tab(entities_page.FIELD_TAGS)
        entities_page.assert_edit_tags_disabled()
        entities_page.assert_remove_tags_disabled()
        entities_page.click_adapters_tab()
        entities_page.click_custom_data_tab()
        assert entities_page.is_custom_data_edit_disabled()
        if table_field:
            entities_page.click_general_tab()
            entities_page.click_tab(table_field)
            entities_page.click_export_csv(False)

    def _test_entities_with_edit_permission(self, entities_page):
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()
        assert not entities_page.is_row_checkbox_absent()
        entities_page.click_row_checkbox()
        assert not entities_page.is_actions_button_disable()
        entities_page.click_row_checkbox()
        entities_page.load_notes()
        assert entities_page.get_add_note_button()
        entities_page.create_note(self.NOTE_TEXT)
        assert entities_page.can_edit_notes()
        assert not entities_page.is_row_checkbox_absent()
        entities_page.click_tab(entities_page.FIELD_TAGS)
        assert entities_page.get_edit_tags_button()
        assert entities_page.get_remove_tags_button()
        entities_page.click_adapters_tab()
        entities_page.click_custom_data_tab()
        assert entities_page.find_custom_data_edit()

    @staticmethod
    def _test_saved_queries_without_any_permission(entities_page, queries_page, query_name):
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()

        entities_page.check_search_list_for_absent_names([query_name])
        entities_page.reset_query()
        entities_page.fill_filter('cb')
        entities_page.enter_search()
        queries_page.switch_to_page()
        queries_page.wait_for_table_to_be_responsive()
        queries_page.is_row_checkbox_absent()
        queries_page.click_query_row_by_name(query_name)
        queries_page.assert_run_query_disabled()
        with pytest.raises(TimeoutException):
            queries_page.get_edit_panel_action()
        with pytest.raises(TimeoutException):
            queries_page.get_remove_panel_action()

    @staticmethod
    def _test_saved_queries_with_run_permission(entities_page, queries_page, query_name):
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()

        entities_page.check_search_list_for_names([query_name])
        entities_page.execute_saved_query(query_name)
        queries_page.switch_to_page()
        queries_page.is_row_checkbox_absent()
        queries_page.click_query_row_by_name(query_name)
        with pytest.raises(TimeoutException):
            queries_page.get_edit_panel_action()
        with pytest.raises(TimeoutException):
            queries_page.get_remove_panel_action()
        queries_page.run_query()

    @staticmethod
    def _test_saved_queries_with_edit_permission(entities_page, queries_page, query_name):
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()

        entities_page.check_search_list_for_names([query_name])
        entities_page.execute_saved_query(query_name)

        queries_page.switch_to_page()
        queries_page.is_row_checkbox_absent()
        queries_page.click_query_row_by_name(query_name)
        queries_page.wait_for_side_panel()
        queries_page.get_edit_panel_action().click()

        queries_page.click_save_changes()
        with pytest.raises(TimeoutException):
            queries_page.get_remove_panel_action()
        # test the enforce button is missing without an Add Enforcement permission
        with pytest.raises(TimeoutException):
            queries_page.get_enforce_panel_action()
        queries_page.run_query()

    @staticmethod
    def _test_saved_queries_with_create_permission(entities_page, query_name):
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()
        entities_page.fill_filter('cb')
        entities_page.enter_search()
        entities_page.open_actions_query()
        assert not entities_page.is_query_save_disabled()
        entities_page.open_actions_query()
        entities_page.run_filter_and_save(query_name, JSON_ADAPTER_FILTER)

    @staticmethod
    def _test_saved_queries_with_delete_permission(entities_page, queries_page, query_name, new_query_name):
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()

        queries_page.switch_to_page()
        queries_page.check_query_by_name(query_name)
        queries_page.remove_selected_queries(True)
        queries_page.click_query_row_by_name(new_query_name)
        queries_page.get_remove_panel_action().click()
        queries_page.safeguard_click_confirm(queries_page.SAFEGUARD_REMOVE_BUTTON_SINGLE)

    def _test_saved_queries_with_add_enforcement(self, entities_page, queries_page, query_name):
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()

        queries_page.switch_to_page()
        queries_page.wait_for_table_to_be_responsive()
        queries_page.click_query_row_by_name(query_name)
        queries_page.wait_for_side_panel()
        queries_page.get_enforce_panel_action().click()
        self.enforcements_page.fill_enforcement_name(self.enforcements_page.DUMMY_ENFORCEMENT_NAME)
        self.enforcements_page.add_tag_entities()
        self.enforcements_page.select_trigger()
        assert self.enforcements_page.get_selected_saved_view_name() == query_name

    def _test_enforcements_without_view_tasks_permissions(self, enforcement_set_id):
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row()
        self.devices_page.click_enforcement_tasks_tab()
        self.devices_page.search_enforcement_tasks_search_input(enforcement_set_id)
        assert self.devices_page.get_enforcement_tasks_count() == 1
        self.devices_page.search_enforcement_tasks_search_input(enforcement_set_id + '1')
        assert self.devices_page.get_enforcement_tasks_count() == 0
        self.devices_page.search_enforcement_tasks_search_input('')
        self.devices_page.wait_for_table_to_load()
        with pytest.raises(NoSuchElementException):
            self.devices_page.click_task_name(enforcement_set_id)

    def _find_enforcement_task_id(self):
        self.enforcements_page.find_task_action_success(self.RUN_TAG_ENFORCEMENT_NAME).click()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row()
        self.devices_page.click_enforcement_tasks_tab()
        table_data = self.devices_page.get_field_table_data_with_ids()
        assert len(table_data) == 1
        enforcement_set_id, enforcement_set_name, action_name, is_success, output = table_data[0]
        return enforcement_set_id

    def _test_enforcements_with_view_tasks_permissions(self, enforcement_set_id):
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.click_row()
        self.devices_page.click_enforcement_tasks_tab()
        self.assert_device_enforcement_task(enforcement_set_id)

    def _test_run_enforcement_permission(self, entities_page, settings_permissions, user_role):
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()
        entities_page.click_row_checkbox(make_yes=True)
        entities_page.open_actions_menu()
        assert self.devices_page.is_enforce_button_disabled(self.devices_page.TABLE_ACTIONS_RUN_ENFORCE)
        assert self.devices_page.is_enforce_button_disabled(self.devices_page.TABLE_ACTIONS_ADD_ENFORCE)
        entities_page.close_actions_dropdown()
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'enforcements',
                                                     'Run Enforcement',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()
        entities_page.click_row_checkbox(make_yes=True)
        entities_page.open_actions_menu()
        # The "run existing enforcement" button should still be disabled since there aren't any
        # enforcements yet
        assert entities_page.is_enforce_button_disabled(self.devices_page.TABLE_ACTIONS_RUN_ENFORCE)
        assert self.devices_page.is_enforce_button_disabled(self.devices_page.TABLE_ACTIONS_ADD_ENFORCE)
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'enforcements',
                                                     'Add Enforcement',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        entities_page.switch_to_page()
        entities_page.wait_for_table_to_load()
        entities_page.click_row_checkbox(make_yes=True)
        entities_page.open_actions_menu()
        assert not self.devices_page.is_enforce_button_disabled(self.devices_page.TABLE_ACTIONS_ADD_ENFORCE)
        self.devices_page.close_actions_dropdown()
        # Create a random enforcement in order to check that the "run existing enforcement"
        # is no longer disabled
        self.devices_page.create_and_run_tag_enforcement(self.DUMMY_ENFORCEMENT_NAME,
                                                         self.DUMMY_ACTION_NAME,
                                                         self.DUMMY_TAG_NAME)
        self.devices_page.wait_for_table_to_be_responsive()
        entities_page.click_row_checkbox()
        entities_page.open_actions_menu()
        assert not entities_page.is_enforce_button_disabled(self.devices_page.TABLE_ACTIONS_RUN_ENFORCE)
