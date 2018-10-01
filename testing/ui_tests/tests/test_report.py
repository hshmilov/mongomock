from services.standalone_services.smtp_server import SMTPService
from ui_tests.tests import ui_consts
from ui_tests.tests.ui_test_base import TestBase


class TestReport(TestBase):
    def test_test_now_no_email_server(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_send_emails_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=False)
        self.settings_page.click_save_button()

        self.report_page.switch_to_page()
        self.report_page.fill_email(ui_consts.VALID_EMAIL)
        self.report_page.click_test_now()
        self.report_page.find_no_email_server_toaster()

    def test_test_now_with_email_server(self):
        smtp_service = SMTPService()
        smtp_service.take_process_ownership()

        with smtp_service.contextmanager():
            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            toggle = self.settings_page.find_send_emails_toggle()
            self.settings_page.click_toggle_button(toggle, make_yes=True)
            self.settings_page.fill_email_host(smtp_service.name)
            self.settings_page.fill_email_port(smtp_service.port)
            self.settings_page.click_save_button()

            self.report_page.switch_to_page()
            self.report_page.fill_email(ui_consts.VALID_EMAIL)
            self.report_page.click_test_now()
            self.report_page.find_email_sent_toaster()
