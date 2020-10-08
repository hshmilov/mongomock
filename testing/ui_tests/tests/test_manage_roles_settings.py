from ui_tests.tests.ui_test_base import TestBase

NEW_ROLE_PANEL_TITLE = 'New Role'
TEST_ROLE_NAME = 'Example Role'


class TestManageRolesSettings(TestBase):
    def test_add_new_role_panel_title(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_roles_settings()
        self.settings_page.wait_for_table_to_load()
        self.settings_page.click_new_role()
        self.settings_page.wait_for_role_panel_present()
        assert self.settings_page.get_role_panel_title() == NEW_ROLE_PANEL_TITLE

    def test_edit_existing_role_panel_title(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_manage_roles_settings()
        self.settings_page.wait_for_table_to_load()
        self.settings_page.create_new_role(TEST_ROLE_NAME, [])
        self.settings_page.click_role_by_name(TEST_ROLE_NAME)
        assert self.settings_page.get_role_panel_title() == TEST_ROLE_NAME
        self.settings_page.get_role_remove_panel_action().click()
        self.settings_page.wait_for_role_removed_successfully_toaster()
