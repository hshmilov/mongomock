from services.standalone_services.maildiranasaurus_service import MaildiranasaurusService
from services.standalone_services.smtp_service import generate_random_valid_email
from services.standalone_services.syslog_service import SyslogService
from ui_tests.pages.reports_page import ReportFrequency
from ui_tests.tests.test_report_base import TestReportGenerationBase
from ui_tests.tests.ui_consts import VALID_EMAIL, Reports
from axonius.consts.gui_consts import DASHBOARD_SPACE_DEFAULT


class TestReportSettings(TestReportGenerationBase):
    def test_reports_saved(self):
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_spinner_to_end()
        assert self.reports_page.get_table_number_of_rows() == 2

    def test_report_email_settings(self):
        self.reports_page.open_report(Reports.test_report_with_email)
        assert self.reports_page.is_frequency_set(ReportFrequency.weekly)
        emails = self.reports_page.get_emails()
        assert len(emails) == 1
        assert emails[0] == VALID_EMAIL

    def test_default_spaces(self):
        self.reports_page.switch_to_page()
        self.reports_page.click_new_report()
        spaces_options = self.reports_page.get_space_select_options()
        assert spaces_options.count(DASHBOARD_SPACE_DEFAULT) == 1

    def test_report_generation(self):
        self.reports_page.open_report(Reports.test_report_with_email)
        recipient = generate_random_valid_email()
        self.reports_page.edit_email(recipient)
        self.reports_page.click_save()
        self.reports_page.wait_for_table_to_load()
        self.reports_page.wait_for_report_generation(Reports.test_report_with_email)
        doc = self._enter_and_get_report_pdf_doc_from_endpoint(Reports.test_report_with_email)
        texts = [page.extractText() for page in doc.pages]
        text = ' '.join(texts)
        assert Reports.test_report_with_email in text
        smtp_service = MaildiranasaurusService()
        with smtp_service.contextmanager(take_ownership=True), SyslogService().contextmanager(take_ownership=True):
            self.settings_page.add_email_server(smtp_service.fqdn, smtp_service.port)
            self.reports_page.open_report(Reports.test_report_with_email)
            self.reports_page.click_send_email()
            self.reports_page.find_email_sent_toaster()
            assert self.reports_page.UPGRADE_EMAIL_SUBJECT_ID in smtp_service.get_email_subject(recipient)
