from ui_tests.tests.ui_test_base import TestBase
from test_credentials.test_gui_credentials import DEFAULT_USER


class TestCloudComplianceEnforcements(TestBase):

    def test_cloud_compliance_ec_lock(self):
        self.login_page.logout_and_login_with_admin()
        self.settings_page.toggle_enforcement_feature_tag(False)

        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        self.settings_page.enable_and_display_compliance()
        self.settings_page.save_and_wait_for_toaster()

        self.compliance_page.switch_to_page()
        self.compliance_page.click_enforce_menu()
        assert self.compliance_page.is_enforcement_lock_modal_visible()
        self.compliance_page.close_feature_lock_tip()
        assert not self.compliance_page.is_enforcement_lock_modal_visible()

        self.settings_page.toggle_enforcement_feature_tag(True)
        self.compliance_page.switch_to_page()
        self.compliance_page.click_enforce_menu()
        assert self.compliance_page.is_enforcement_actions_menu_visible()

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=DEFAULT_USER['user_name'], password=DEFAULT_USER['password'])
