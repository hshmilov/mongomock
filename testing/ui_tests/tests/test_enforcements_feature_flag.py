from ui_tests.tests.ui_test_base import TestBase


class TestEnforcementFeatureFlags(TestBase):
    ENFORCEMENTS_FEATURE_TAG_TITLE = 'Enable Enforcement Center'

    def _toggle_enforcement_feature_tag(self, value):
        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        cloud_visible_toggle = self.settings_page.find_checkbox_by_label(self.ENFORCEMENTS_FEATURE_TAG_TITLE)
        self.settings_page.click_toggle_button(cloud_visible_toggle, make_yes=value)
        self.settings_page.save_and_wait_for_toaster()

    def test_enforcement_page_with_lock(self):
        self.login_page.logout_and_login_with_admin()
        self._toggle_enforcement_feature_tag(False)
        self.enforcements_page.switch_to_page()
        self.enforcements_page.assert_lock_modal_is_visible()
        self.dashboard_page.switch_to_page()
        self._toggle_enforcement_feature_tag(True)

    def test_devices_enforcement_action(self):
        self.login_page.logout_and_login_with_admin()
        self._toggle_enforcement_feature_tag(False)

        self.settings_page.switch_to_page()
        self.base_page.run_discovery()

        self.devices_page.switch_to_page()
        self.devices_page.wait_for_table_to_load()
        self.devices_page.toggle_select_all_rows_checkbox()
        self.devices_page.open_enforce_dialog()
        self.enforcements_page.assert_lock_modal_is_visible()
        self.dashboard_page.switch_to_page()
        self._toggle_enforcement_feature_tag(True)
