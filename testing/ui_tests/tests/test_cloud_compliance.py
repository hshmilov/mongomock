import pytest

from test_credentials.test_gui_credentials import AXONIUS_USER
from test_credentials.test_aws_credentials import client_details as aws_client_details
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import AWS_ADAPTER_NAME, AWS_ADAPTER
from services.adapters.aws_service import AwsService
from services.plugins.compliance_service import ComplianceService


class TestCloudCompliance(TestBase):

    def test_cloud_compliance_tip(self):
        self.devices_page.switch_to_page()
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()

        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])
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
        self._restore_feature_flags(False)

    def test_cloud_compliance_default_rules(self):
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
        self.compliance_page.assert_no_compliance_tip()
        self.compliance_page.assert_default_compliance_roles()

        self.compliance_page.click_specific_row_by_field_value('Section', '1.6')
        self.compliance_page.assert_compliance_panel_is_open()
        self._restore_feature_flags(True)

    def _restore_feature_flags(self, restore_cloud_visible):
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()
        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])
        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        self.settings_page.fill_trial_expiration_by_remainder(28)
        self.settings_page.toggle_compliance_enable_feature(False)
        if restore_cloud_visible:
            self.settings_page.toggle_compliance_visible_feature(False)
        self.settings_page.save_and_wait_for_toaster()

    @pytest.mark.skip('AX-7569')
    def test_compliance_score(self):
        self.devices_page.switch_to_page()
        self.login_page.logout()
        self.login_page.wait_for_login_page_to_load()

        self.login_page.login(username=AXONIUS_USER['user_name'], password=AXONIUS_USER['password'])
        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        self.settings_page.enable_and_display_compliance()
        self.settings_page.save_and_wait_for_toaster()

        try:
            with AwsService().contextmanager(take_ownership=True), \
                    ComplianceService().contextmanager(take_ownership=True):
                self.adapters_page.wait_for_adapter(AWS_ADAPTER_NAME)
                self.adapters_page.create_new_adapter_connection(AWS_ADAPTER_NAME, aws_client_details[0][0])

                self.settings_page.switch_to_page()
                self.base_page.run_discovery()
                self.compliance_page.switch_to_page()

                failed_rules = self.compliance_page.get_total_failed_rules()
                passed_rules = self.compliance_page.get_total_passed_rules()
                current_score = self.compliance_page.get_current_score_value()

                assert round((passed_rules / (passed_rules + failed_rules)) * 100) == current_score

                self.adapters_page.switch_to_page()
                self.adapters_page.clean_adapter_servers(AWS_ADAPTER_NAME)
        finally:
            self.wait_for_adapter_down(AWS_ADAPTER)
            self._restore_feature_flags(True)
