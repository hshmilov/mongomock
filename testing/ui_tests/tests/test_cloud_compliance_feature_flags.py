import time

import pytest

from ui_tests.tests.ui_test_base import TestBase


class TestCloudComplianceFeatureFlags(TestBase):

    @pytest.mark.skip('AX-8127')
    def test_cloud_compliance_expiry_date(self):
        self.login_page.logout_and_login_with_admin()
        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        self.settings_page.fill_trial_expiration_by_remainder(None)
        self.settings_page.enable_and_display_compliance()
        self.settings_page.fill_compliance_expiration_by_remainder(1)
        self.settings_page.save_and_wait_for_toaster()
        self.login_page.logout()
        self.login()

        self.compliance_page.switch_to_page()
        time.sleep(0.5)
        self.compliance_page.assert_no_compliance_expiry_modal()

        self.login_page.logout_and_login_with_admin()
        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        self.settings_page.fill_compliance_expiration_by_remainder(-1)
        self.settings_page.save_and_wait_for_toaster()
        self.login_page.logout()
        self.login()

        self.compliance_page.switch_to_page()
        time.sleep(0.5)
        self.compliance_page.assert_compliance_expiry_modal()

        # Revert
        self.login_page.logout_and_login_with_admin()
        self.settings_page.switch_to_page()
        self.settings_page.click_feature_flags()
        self.settings_page.fill_compliance_expiration_by_remainder(None)
        self.settings_page.restore_feature_flags(False)
