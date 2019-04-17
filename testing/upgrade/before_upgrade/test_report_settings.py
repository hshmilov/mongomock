from ui_tests.pages.reports_page import ReportFrequency
from ui_tests.tests.ui_consts import VALID_EMAIL, EmailSettings, Reports
from ui_tests.tests.ui_test_base import TestBase


class TestPrepareReportSettings(TestBase):
    def test_report_no_email_settings(self):
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        self.reports_page.click_new_report()
        self.reports_page.click_add_scheduling()
        self.reports_page.find_missing_email_server_notification()
        self.reports_page.fill_report_name(Reports.test_report_no_email)
        self.reports_page.click_include_dashboard()
        self.reports_page.click_save()

    def test_report_with_email_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.set_send_emails_toggle()
        self.settings_page.fill_email_host(EmailSettings.host)
        self.settings_page.fill_email_port(EmailSettings.port)
        self.settings_page.save_and_wait_for_toaster()
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        self.reports_page.click_new_report()
        self.reports_page.click_add_scheduling()
        self.reports_page.fill_report_name(Reports.test_report_with_email)
        self.reports_page.fill_email_subject(Reports.test_report_with_email)
        self.reports_page.click_include_dashboard()
        self.reports_page.fill_email(VALID_EMAIL)
        self.reports_page.select_frequency(ReportFrequency.weekly)
        self.reports_page.click_save()
