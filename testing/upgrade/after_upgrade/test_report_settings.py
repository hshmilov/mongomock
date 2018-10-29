from ui_tests.pages.report_page import ReportFrequency
from ui_tests.tests.ui_consts import VALID_EMAIL
from ui_tests.tests.ui_test_base import TestBase


class TestReportSettings(TestBase):
    def test_email_settings(self):
        self.report_page.switch_to_page()
        self.report_page.wait_for_spinner_to_end()
        assert self.report_page.is_frequency_set(ReportFrequency.weekly)
        assert self.report_page.get_email() == VALID_EMAIL
