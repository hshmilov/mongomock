from ui_tests.pages.report_page import ReportFrequency
from ui_tests.tests.ui_consts import VALID_EMAIL
from ui_tests.tests.ui_test_base import TestBase


class TestPrepareReportSettings(TestBase):
    def test_email_settings(self):
        self.report_page.switch_to_page()
        self.report_page.wait_for_table_to_load()
        self.report_page.fill_email(VALID_EMAIL)
        self.report_page.select_frequency(ReportFrequency.weekly)
        self.report_page.click_save()
