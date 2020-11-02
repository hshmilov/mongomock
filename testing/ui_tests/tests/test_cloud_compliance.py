from test_credentials.test_gui_credentials import AXONIUS_USER, DEFAULT_USER
from ui_tests.tests.ui_test_base import TestBase


class TestCloudCompliance(TestBase):

    def test_cloud_compliance_tip(self):
        self.login_page.logout_and_login_with_admin()

        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        self.settings_page.fill_trial_expiration_by_remainder(None)
        cloud_visible_toggle = self.settings_page.find_toggle_with_label_by_label('Cloud Visible')
        self.settings_page.click_toggle_button(cloud_visible_toggle, make_yes=True)
        self.settings_page.save_and_wait_for_toaster()
        self.login_page.logout()
        self.login()
        self.compliance_page.switch_to_page()
        self.compliance_page.assert_compliance_tip()
        self.login_page.switch_user(AXONIUS_USER['user_name'], AXONIUS_USER['password'])
        self.settings_page.restore_feature_flags(False)

    def test_cloud_compliance_default_rules(self):
        self.login_page.logout_and_login_with_admin()

        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        self.settings_page.enable_and_display_compliance()
        self.settings_page.save_and_wait_for_toaster()

        self.settings_page.click_manage_users_settings()
        self.compliance_page.switch_to_page()
        self.compliance_page.wait_for_table_to_load()
        self.compliance_page.assert_no_compliance_tip()
        self.compliance_page.assert_default_compliance_roles()

        self.compliance_page.click_specific_row_by_field_value('Section', '1.6')
        self.compliance_page.assert_compliance_panel_is_open()
        self.login_page.switch_user(AXONIUS_USER['user_name'], AXONIUS_USER['password'])
        self.settings_page.restore_feature_flags(True)

        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(DEFAULT_USER['user_name'], DEFAULT_USER['password'])
