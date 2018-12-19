import os

from services.standalone_services.smtp_server import SMTPService, generate_random_valid_email
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
            self.settings_page.fill_email_host(smtp_service.fqdn)
            self.settings_page.fill_email_port(smtp_service.port)
            self.settings_page.click_save_button()

            self.report_page.switch_to_page()

            recipient = generate_random_valid_email()
            self.report_page.fill_email(recipient)

            self.report_page.click_test_now()
            self.report_page.find_email_sent_toaster()

            smtp_service.verify_email_send(recipient)

        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_send_emails_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=False)
        self.settings_page.click_save_button()

    def test_test_now_with_tls_email_server(self):
        smtp_service = SMTPService()
        smtp_service.take_process_ownership()

        with smtp_service.contextmanager():
            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            toggle = self.settings_page.find_send_emails_toggle()
            self.settings_page.click_toggle_button(toggle, make_yes=True)
            self.settings_page.fill_email_host(smtp_service.fqdn)
            self.settings_page.fill_email_port(smtp_service.port)
            goguerrilla_basedir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                               '../../services/standalone_services/goguerrilla'))

            ca_data = open(os.path.join(goguerrilla_basedir, 'rootca.test.pem'), 'r').read()
            cert_data = open(os.path.join(goguerrilla_basedir, 'client.test.pem'), 'r').read()
            private_data = open(os.path.join(goguerrilla_basedir, 'client.test.key'), 'r').read()

            self.settings_page.set_email_ssl_files(ca_data, cert_data, private_data)
            self.settings_page.click_save_button()

            self.report_page.switch_to_page()

            recipient = generate_random_valid_email()
            self.report_page.fill_email(recipient)

            self.report_page.click_test_now()
            self.report_page.find_email_sent_toaster()

            smtp_service.verify_email_send(recipient)

        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_send_emails_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=False)
        self.settings_page.click_save_button()
