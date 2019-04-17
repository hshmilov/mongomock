import os
import time

from services.standalone_services.smtp_server import SMTPService, generate_random_valid_email
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import EmailSettings


class TestReport(TestBase):
    PERIOD_DAILY = 'period-daily'
    PERIOD_WEEKLY = 'period-weekly'
    PERIOD_DAILY = 'period-daily'
    DISABLED_CLASS = 'disabled'
    REPORT_SUBJECT = 'axonius report subject'

    def test_report_name(self):
        self.reports_page.get_to_new_report_page()
        self.reports_page.fill_report_name('test')

    def test_add_saved_query(self):
        self.reports_page.get_to_new_report_page()
        self.reports_page.click_include_queries()
        self.reports_page.click_add_query()
        assert self.reports_page.get_queries_count() == 2

    def test_remove_query(self):
        self.reports_page.get_to_new_report_page()
        self.reports_page.click_include_queries()
        self.reports_page.click_add_query()
        self.reports_page.click_remove_query(1)
        assert self.reports_page.get_queries_count() == 1

    def test_add_scheduling(self):
        smtp_service = SMTPService()
        smtp_service.take_process_ownership()

        with smtp_service.contextmanager():
            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()

            self.settings_page.set_send_emails_toggle()

            self.settings_page.fill_email_host(EmailSettings.host)
            self.settings_page.fill_email_port(EmailSettings.port)
            self.settings_page.save_and_wait_for_toaster()

            self.reports_page.get_to_new_report_page()
            report_name = 'test_scheduling'
            self.reports_page.fill_report_name(report_name)
            self.reports_page.click_include_dashboard()
            self.reports_page.click_add_scheduling()
            self.reports_page.fill_email_subject(report_name)
            recipient = generate_random_valid_email()
            self.reports_page.fill_email(recipient)
            self.reports_page.select_frequency(self.PERIOD_DAILY)
            self.reports_page.click_save()

            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            self.settings_page.set_dont_send_emails_toggle()
            self.settings_page.save_and_wait_for_toaster()

            self.reports_page.switch_to_page()
            self.reports_page.wait_for_table_to_load()
            self.reports_page.click_report(report_name)
            self.reports_page.wait_for_send_mail_button()
            assert self.reports_page.is_frequency_set(self.PERIOD_DAILY)
            assert self.reports_page.is_generated()

    def test_save_disabled(self):
        self.reports_page.switch_to_page()
        self.reports_page.get_to_new_report_page()
        assert self.reports_page.is_save_button_disabled()

    def test_save_enabled_all_saved_queries(self):
        self.reports_page.get_to_new_report_page()
        self.reports_page.fill_report_name('test report')
        self.reports_page.click_include_dashboard()
        assert self.DISABLED_CLASS not in self.reports_page.get_save_button().get_attribute('class')

    def test_no_email_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.set_dont_send_emails_toggle()
        self.settings_page.save_and_wait_for_toaster()

        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        self.reports_page.click_new_report()
        self.reports_page.click_add_scheduling()
        self.reports_page.find_missing_email_server_notification()

    def test_test_now_with_email_server(self):
        smtp_service = SMTPService()
        smtp_service.take_process_ownership()

        with smtp_service.contextmanager():
            self.settings_page.switch_to_page()
            # to stop "No report generated. Press "Discover Now" to generate."
            self.base_page.run_discovery()

            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            toggle = self.settings_page.find_send_emails_toggle()
            self.settings_page.click_toggle_button(toggle, make_yes=True, scroll_to_toggle=False)
            self.settings_page.fill_email_host(smtp_service.fqdn)
            self.settings_page.fill_email_port(smtp_service.port)
            self.settings_page.click_save_button()

            self.reports_page.switch_to_page()
            self.reports_page.click_new_report()
            recipient = generate_random_valid_email()
            self.reports_page.fill_report_name(recipient)
            self.reports_page.click_include_dashboard()
            self.reports_page.click_add_scheduling()
            self.reports_page.fill_email_subject(self.REPORT_SUBJECT)
            self.reports_page.fill_email(recipient)
            self.reports_page.click_save()
            self.reports_page.wait_for_table_to_load()
            self.reports_page.click_report(recipient)
            self.reports_page.wait_for_send_mail_button()
            self.reports_page.click_send_email()
            self.reports_page.find_email_sent_toaster()

            smtp_service.verify_email_send(recipient)

        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_send_emails_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=False, scroll_to_toggle=False)
        self.settings_page.click_save_button()

    def test_test_now_with_tls_email_server(self):
        smtp_service = SMTPService()
        smtp_service.take_process_ownership()

        with smtp_service.contextmanager():
            self.settings_page.switch_to_page()
            # to stop "No report generated. Press "Discover Now" to generate."
            self.base_page.run_discovery()

            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            toggle = self.settings_page.find_send_emails_toggle()
            self.settings_page.click_toggle_button(toggle, make_yes=True, scroll_to_toggle=False)
            self.settings_page.fill_email_host(smtp_service.fqdn)
            self.settings_page.fill_email_port(smtp_service.port)
            goguerrilla_basedir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                               '../../services/standalone_services/goguerrilla'))

            ca_data = open(os.path.join(goguerrilla_basedir, 'rootca.test.pem'), 'r').read()
            cert_data = open(os.path.join(goguerrilla_basedir, 'client.test.pem'), 'r').read()
            private_data = open(os.path.join(goguerrilla_basedir, 'client.test.key'), 'r').read()

            self.settings_page.set_email_ssl_files(ca_data, cert_data, private_data)
            self.settings_page.set_email_ssl_verification('Unverified')
            self.settings_page.click_save_button()

            self.reports_page.switch_to_page()
            self.reports_page.click_new_report()
            recipient = generate_random_valid_email()
            self.reports_page.fill_report_name(recipient)
            self.reports_page.click_include_dashboard()
            self.reports_page.click_add_scheduling()
            self.reports_page.fill_email_subject(self.REPORT_SUBJECT)
            self.reports_page.fill_email(recipient)
            self.reports_page.click_save()
            time.sleep(5)
            self.reports_page.click_report(recipient)
            self.reports_page.click_send_email()
            self.reports_page.find_email_sent_toaster()

            smtp_service.verify_email_send(recipient)

        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_send_emails_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=False, scroll_to_toggle=False)
        self.settings_page.click_save_button()
