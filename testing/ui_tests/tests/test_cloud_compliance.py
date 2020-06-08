from test_credentials.test_gui_credentials import AXONIUS_USER, DEFAULT_USER
from test_credentials.test_aws_credentials import client_details as aws_client_details
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import AWS_ADAPTER_NAME, AWS_ADAPTER
from services.adapters.aws_service import AwsService
from services.plugins.compliance_service import ComplianceService


class TestCloudCompliance(TestBase):

    RULE_FILTER = '1.1 Avoid the use of the "root" Account'
    CATEGORY_FILTER = 'Logging'

    def test_cloud_compliance_tip(self):
        self.login_page.logout_and_login_with_admin()

        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        self.settings_page.fill_trial_expiration_by_remainder(None)
        cloud_visible_toggle = self.settings_page.find_checkbox_by_label('Cloud Visible')
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

    def test_compliance_filters(self):
        self.login_page.switch_user(AXONIUS_USER['user_name'], AXONIUS_USER['password'])
        self.settings_page.toggle_compliance_feature()

        try:
            with AwsService().contextmanager(take_ownership=True), \
                    ComplianceService().contextmanager(take_ownership=True):
                self.adapters_page.wait_for_adapter(AWS_ADAPTER_NAME)
                self.adapters_page.create_new_adapter_connection(AWS_ADAPTER_NAME, aws_client_details[0][0])

                self.settings_page.switch_to_page()
                self.base_page.run_discovery()
                self.compliance_page.switch_to_page()

                self.compliance_page.switch_to_page()

                self.compliance_page.open_rule_filter_dropdown()
                self.compliance_page.toggle_filter(self.RULE_FILTER)
                rules = self.compliance_page.get_all_rules()
                assert len(rules) == 1
                self.compliance_page.toggle_filter(self.RULE_FILTER)

                self.compliance_page.open_category_filter_dropdown()
                self.compliance_page.toggle_filter(self.CATEGORY_FILTER)
                rules = self.compliance_page.get_all_rules()
                assert len(rules) == 9

                # Testing the that filter is saved on the cis state.
                self.dashboard_page.switch_to_page()
                self.compliance_page.switch_to_page()
                rules = self.compliance_page.get_all_rules()
                assert len(rules) == 9

                self.adapters_page.switch_to_page()
                self.adapters_page.clean_adapter_servers(AWS_ADAPTER_NAME)
        finally:
            self.wait_for_adapter_down(AWS_ADAPTER)
            self.settings_page.restore_feature_flags(True)
