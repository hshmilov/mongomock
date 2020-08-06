from ui_tests.tests.ui_test_base import TestBase


class TestEnforcementFeatureFlags(TestBase):
    ENFORCEMENTS_FEATURE_TAG_TITLE = 'Enable Enforcement Center'
    DUMMY_ENFORCEMENT_NAME = 'Dummy Enforcement'
    DUMMY_ACTION_NAME = 'Dummy Action Name'
    DUMMY_TAG_NAME = 'Dummy Tag Name'

    def test_enforcement_page_with_lock(self):
        self.login_page.logout_and_login_with_admin()
        self.settings_page.toggle_enforcement_feature_tag(False)
        self.enforcements_page.switch_to_page()
        self.enforcements_page.assert_lock_modal_is_visible()
        self.dashboard_page.switch_to_page()
        self.settings_page.toggle_enforcement_feature_tag(True)

    def test_devices_enforcement_action(self):
        self.login_page.logout_and_login_with_admin()
        self.settings_page.switch_to_page()
        self.base_page.run_discovery()
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.click_row_checkbox()
        self.devices_page.create_and_run_tag_enforcement(self.DUMMY_ENFORCEMENT_NAME,
                                                         self.DUMMY_ACTION_NAME,
                                                         self.DUMMY_TAG_NAME)
        self.devices_page.wait_for_table_to_be_responsive()
        self.settings_page.toggle_enforcement_feature_tag(False)
        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_be_responsive()
        self.devices_page.toggle_select_all_rows_checkbox()
        self.devices_page.open_enforce_dialog()
        self.enforcements_page.assert_lock_modal_is_visible()
        self.dashboard_page.switch_to_page()
        self.settings_page.toggle_enforcement_feature_tag(True)
