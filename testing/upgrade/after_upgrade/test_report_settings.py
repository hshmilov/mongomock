from ui_tests.pages.reports_page import ReportFrequency
from ui_tests.tests.ui_consts import VALID_EMAIL, Reports
from ui_tests.tests.ui_test_base import TestBase
from axonius.consts.gui_consts import DASHBOARD_SPACE_DEFAULT


class TestReportSettings(TestBase):
    def test_reports_saved(self):
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_spinner_to_end()
        assert self.reports_page.get_table_number_of_rows() == 2

    def test_report_email_settings(self):
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_spinner_to_end()
        self.reports_page.click_report(Reports.test_report_with_email)
        assert self.reports_page.is_frequency_set(ReportFrequency.weekly)
        emails = self.reports_page.get_emails()
        assert len(emails) == 1
        assert emails[0] == VALID_EMAIL

    def test_default_spaces(self):
        self.reports_page.switch_to_page()
        self.reports_page.click_new_report()
        self.reports_page.click_include_dashboard()
        spaces_options = self.reports_page.get_spaces_options()
        assert spaces_options.count(DASHBOARD_SPACE_DEFAULT) == 1
