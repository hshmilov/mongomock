from ui_tests.tests.ui_test_base import TestBase
from services.standalone_services.smtp_server import SMTPService

INVALID_EMAIL_HOST = 'dada...$#@'


class TestGlobalSettings(TestBase):
    def test_email_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_send_emails_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=True)

        # Invalid host is not being tested, an open bug
        # self.settings_page.fill_email_host(INVALID_EMAIL_HOST)

        self.settings_page.fill_email_port(-5)
        self.settings_page.find_email_port_error()

        # Ports above the maximum are also not validated
        # self.settings_page.fill_email_port(555)
        # self.settings_page.fill_email_port(88888)
        # self.settings_page.find_email_port_error()

    def test_email_host_validation(self):
        smtp_service = SMTPService()
        smtp_service.take_process_ownership()

        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_send_emails_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=True)

        self.settings_page.fill_email_host(smtp_service.name)
        self.settings_page.fill_email_port(smtp_service.port)

        self.settings_page.click_save_button()
        self.settings_page.find_email_connection_failure_toaster(smtp_service.name)

        with smtp_service.contextmanager():
            self.settings_page.click_save_button()
            self.settings_page.find_saved_successfully_toaster()
