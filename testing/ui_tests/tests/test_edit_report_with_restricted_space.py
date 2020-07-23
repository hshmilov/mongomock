from ui_tests.pages.reports_page import ReportConfig
from ui_tests.tests import ui_consts
from ui_tests.tests.permissions_test_base import PermissionsTestBase


class TestEditReportWithRestrictedSpace(PermissionsTestBase):
    def test_edit_report_with_restricted_space(self):
        self.base_page.run_discovery()
        self.settings_page.add_user_with_duplicated_role(ui_consts.VIEWER_USERNAME,
                                                         ui_consts.NEW_PASSWORD,
                                                         ui_consts.FIRST_NAME,
                                                         ui_consts.LAST_NAME,
                                                         self.settings_page.VIEWER_ROLE)
        self.dashboard_page.switch_to_page()
        self.dashboard_page.add_new_space(self.TEST_SPACE_NAME, [self.settings_page.VIEWER_ROLE])
        self.reports_page.switch_to_page()
        self.reports_page.create_report(ReportConfig(report_name=self.TEST_REPORT_NAME, add_dashboard=True,
                                                     spaces=[self.TEST_SPACE_NAME]))
        self.reports_page.wait_for_table_to_load()
        self.reports_page.click_report(self.TEST_REPORT_NAME)
        self.reports_page.wait_for_spinner_to_end()
        assert not self.reports_page.is_dashboard_checkbox_disabled()
        self.login_page.switch_user(ui_consts.VIEWER_USERNAME, ui_consts.NEW_PASSWORD)
        self.dashboard_page.wait_for_spinner_to_end()
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        self.reports_page.click_report(self.TEST_REPORT_NAME)
        self.reports_page.wait_for_spinner_to_end()
        assert self.reports_page.is_restricted_report_modal_exist()
        self.reports_page.click_restricted_report_modal_confirm()
        self.reports_page.wait_for_table_to_be_responsive()
        self.login_page.logout_and_login_with_admin()
