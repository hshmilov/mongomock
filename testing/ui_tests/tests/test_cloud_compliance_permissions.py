from test_credentials.test_gui_credentials import AXONIUS_USER
from ui_tests.tests import ui_consts
from ui_tests.tests.permissions_test_base import PermissionsTestBase

# pylint: disable=no-member


class TestInstancesPermissions(PermissionsTestBase):

    def test_cloud_compliance_permissions(self):
        self.devices_page.switch_to_page()
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()

        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])
        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        cloud_visible_toggle = self.settings_page.find_checkbox_by_label('Cloud Visible')
        self.settings_page.click_toggle_button(cloud_visible_toggle, make_yes=True)
        cloud_enabled_toggle = self.settings_page.find_checkbox_by_label('Cloud Enabled')
        self.settings_page.click_toggle_button(cloud_enabled_toggle, make_yes=True)
        self.settings_page.save_and_wait_for_toaster()
        self.settings_page.click_manage_users_settings()
        self.compliance_page.switch_to_page()
        self.compliance_page.wait_for_table_to_load()
        self.compliance_page.assert_default_compliance_roles()

        # Create user with Restricted role and check permissions correct also after refresh
        user_role = self.settings_page.add_user_with_duplicated_role(ui_consts.RESTRICTED_USERNAME,
                                                                     ui_consts.NEW_PASSWORD,
                                                                     ui_consts.FIRST_NAME,
                                                                     ui_consts.LAST_NAME,
                                                                     self.settings_page.RESTRICTED_ROLE)

        self.login_page.switch_user(ui_consts.RESTRICTED_USERNAME, ui_consts.NEW_PASSWORD)
        self.dashboard_page.switch_to_page()
        self.compliance_page.assert_screen_is_restricted()
        settings_permissions = {}
        self._add_action_to_role_and_login_with_user(settings_permissions,
                                                     'compliance',
                                                     'View Cloud Asset Compliance',
                                                     user_role,
                                                     ui_consts.RESTRICTED_USERNAME,
                                                     ui_consts.NEW_PASSWORD)
        self.compliance_page.switch_to_page()
        self.compliance_page.wait_for_table_to_load()
        self.compliance_page.assert_default_compliance_roles()
