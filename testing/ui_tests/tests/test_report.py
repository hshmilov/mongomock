import os
import re

from services.adapters import stresstest_scanner_service, stresstest_service
from services.standalone_services.smtp_server import SMTPService, generate_random_valid_email
from ui_tests.pages.reports_page import ReportFrequency
from ui_tests.tests import ui_consts
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import EmailSettings


class TestReport(TestBase):
    DISABLED_CLASS = 'disabled'
    REPORT_SUBJECT = 'axonius report subject'
    TEST_REPORT_EDIT = 'test report edit'
    TEST_REPORT_EDIT_QUERY = 'test report edit query'
    TEST_REPORT_EDIT_QUERY1 = 'test report edit query1'
    TEST_REPORT_READ_ONLY_NAME = 'report for read only'
    TEST_REPORT_READ_ONLY_QUERY = 'query for read only test'
    TEST_DOWNLOAD_NOW_NAME = 'test download now'

    def test_report_name(self):
        self.reports_page.get_to_new_report_page()
        self.reports_page.fill_report_name('test')

    def test_add_saved_query(self):
        self.reports_page.get_to_new_report_page()
        self.reports_page.click_include_queries()
        self.reports_page.click_add_query()
        assert self.reports_page.get_queries_count() == 2
        self.reports_page.click_add_query()
        assert self.reports_page.get_queries_count() == 3

    def test_remove_query(self):
        self.reports_page.get_to_new_report_page()
        self.reports_page.click_include_queries()
        self.reports_page.click_add_query()
        self.reports_page.click_add_query()
        self.reports_page.click_remove_query(1)
        assert self.reports_page.get_queries_count() == 2

    def test_add_scheduling(self):
        smtp_service = SMTPService()
        smtp_service.take_process_ownership()

        with smtp_service.contextmanager():
            self.settings_page.add_email_server(EmailSettings.host, EmailSettings.port)

            self.reports_page.get_to_new_report_page()
            report_name = 'test_scheduling'
            self.reports_page.fill_report_name(report_name)
            self.reports_page.click_include_dashboard()
            self.reports_page.click_add_scheduling()
            self.reports_page.fill_email_subject(report_name)

            self.reports_page.fill_email('test.axonius.com')
            assert self.reports_page.is_custom_error('\'Recipients\' items are not all properly formed')
            emails_str = 'test1@axonius.com,test2@axonius.com;test3@axonius.com'
            self.reports_page.edit_email(emails_str)
            assert self.reports_page.get_emails() == re.compile('[,;]').split(emails_str)
            recipient = generate_random_valid_email()
            self.reports_page.fill_email(recipient)

            self.reports_page.select_frequency(ReportFrequency.daily)
            self.reports_page.click_save()
            self.reports_page.wait_for_table_to_load()
            self.reports_page.wait_for_report_generation(report_name)
            self.reports_page.click_report(report_name)
            self.reports_page.wait_for_spinner_to_end()
            assert self.reports_page.is_frequency_set(ReportFrequency.daily)
            assert self.reports_page.is_generated()
        self.settings_page.remove_email_server()

    def test_save_disabled(self):
        self.reports_page.switch_to_page()
        self.reports_page.get_to_new_report_page()
        assert self.reports_page.is_save_button_disabled()

    def test_download_now(self):
        self.reports_page.get_to_new_report_page()

        self.reports_page.fill_report_name(self.TEST_DOWNLOAD_NOW_NAME)
        self.reports_page.click_include_dashboard()
        assert not self.reports_page.is_report_download_shown()
        self.reports_page.click_save()
        self.reports_page.wait_for_table_to_load()

        self.reports_page.wait_for_report_generation(self.TEST_DOWNLOAD_NOW_NAME)
        self.reports_page.click_report(self.TEST_DOWNLOAD_NOW_NAME)
        self.reports_page.wait_for_spinner_to_end()
        assert self.reports_page.is_report_download_shown()
        self.reports_page.click_report_download()

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
            self.settings_page.add_email_server(smtp_service.fqdn, smtp_service.port)

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
            self.reports_page.wait_for_report_generation(recipient)

            self.reports_page.click_report(recipient)
            self.reports_page.wait_for_send_mail_button()
            self.reports_page.click_send_email()
            self.reports_page.find_email_sent_toaster()

            smtp_service.verify_email_send(recipient)

        self.settings_page.remove_email_server()

    def test_test_now_with_tls_email_server(self):
        smtp_service = SMTPService()
        smtp_service.take_process_ownership()

        with smtp_service.contextmanager():
            self.settings_page.add_email_server(smtp_service.fqdn, smtp_service.port)
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
            self.reports_page.wait_for_report_generation(recipient)
            self.reports_page.click_report(recipient)
            self.reports_page.wait_for_send_mail_button()
            self.reports_page.click_send_email()
            self.reports_page.find_email_sent_toaster()
            smtp_service.verify_email_send(recipient)
        self.settings_page.remove_email_server()

    def test_create_and_edit_report(self):
        smtp_service = SMTPService()
        smtp_service.take_process_ownership()
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        with smtp_service.contextmanager(), stress.contextmanager(take_ownership=True), stress_scanner.contextmanager(
                take_ownership=True):
            device_dict = {'device_count': 10, 'name': 'blah'}
            stress.add_client(device_dict)
            stress_scanner.add_client(device_dict)

            self.base_page.run_discovery()

            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            toggle = self.settings_page.find_send_emails_toggle()
            self.settings_page.click_toggle_button(toggle, make_yes=True, scroll_to_toggle=False)
            self.settings_page.fill_email_host(smtp_service.fqdn)
            self.settings_page.fill_email_port(smtp_service.port)
            self.settings_page.save_and_wait_for_toaster()

            data_query1 = 'specific_data.data.name == regex(\'avigdor no\', \'i\')'
            self.devices_page.create_saved_query(data_query1, self.TEST_REPORT_EDIT_QUERY)
            data_query2 = 'specific_data.data.name == regex(\'avig\', \'i\')'
            self.devices_page.create_saved_query(data_query2, self.TEST_REPORT_EDIT_QUERY1)

            recipient = generate_random_valid_email()

            self.reports_page.create_report(report_name=self.TEST_REPORT_EDIT, add_dashboard=True,
                                            queries=[{'entity': 'Devices', 'name': self.TEST_REPORT_EDIT_QUERY}],
                                            add_scheduling=True, email_subject=self.TEST_REPORT_EDIT,
                                            emails=[recipient], period=ReportFrequency.weekly)
            self.reports_page.wait_for_table_to_load()
            self.reports_page.click_report(self.TEST_REPORT_EDIT)
            self.reports_page.wait_for_spinner_to_end()
            self.reports_page.click_include_dashboard()
            self.reports_page.select_saved_view(self.TEST_REPORT_EDIT_QUERY1, 'Devices')
            new_subject = self.TEST_REPORT_EDIT + '_changed'
            self.reports_page.fill_email_subject(new_subject)
            self.reports_page.select_frequency(ReportFrequency.monthly)
            self.reports_page.click_save()
            self.reports_page.wait_for_table_to_load()
            self.reports_page.wait_for_spinner_to_end()
            self.reports_page.click_report(self.TEST_REPORT_EDIT)
            self.reports_page.wait_for_spinner_to_end()

            assert not self.reports_page.is_include_dashboard()
            assert self.reports_page.is_frequency_set(ReportFrequency.monthly)
            assert self.reports_page.get_email_subject() == new_subject
            assert self.reports_page.get_saved_view() == self.TEST_REPORT_EDIT_QUERY1

    def test_read_only_click_add_scheduling(self):
        smtp_service = SMTPService()
        with smtp_service.contextmanager(take_ownership=True):
            self.settings_page.switch_to_page()
            self.settings_page.click_global_settings()
            toggle = self.settings_page.find_send_emails_toggle()
            self.settings_page.click_toggle_button(toggle, make_yes=True, scroll_to_toggle=False)
            self.settings_page.fill_email_host(smtp_service.fqdn)
            self.settings_page.fill_email_port(smtp_service.port)
            self.settings_page.save_and_wait_for_toaster()
            recipient = generate_random_valid_email()
            self.reports_page.create_report(report_name=self.TEST_REPORT_READ_ONLY_NAME, add_dashboard=True,
                                            queries=None, add_scheduling=True, email_subject=self.REPORT_SUBJECT,
                                            emails=[recipient], period=ReportFrequency.weekly)
            self.reports_page.wait_for_table_to_load()
            # to fill up devices and users
            self.base_page.run_discovery()
            self.settings_page.switch_to_page()
            self.settings_page.click_manage_users_settings()
            self.settings_page.create_new_user(ui_consts.READ_ONLY_USERNAME,
                                               ui_consts.NEW_PASSWORD,
                                               ui_consts.FIRST_NAME,
                                               ui_consts.LAST_NAME)

            self.settings_page.wait_for_user_created_toaster()

            for label in self.settings_page.get_permission_labels():
                self.settings_page.select_permissions(label, self.settings_page.READ_ONLY_PERMISSION)

            self.settings_page.click_save_manage_users_settings()
            self.login_page.logout()
            self.login_page.wait_for_login_page_to_load()
            self.login_page.login(username=ui_consts.READ_ONLY_USERNAME, password=ui_consts.NEW_PASSWORD)

            self.reports_page.switch_to_page()
            self.reports_page.is_disabled_new_report_button()
            self.reports_page.click_report(self.TEST_REPORT_READ_ONLY_NAME)
            self.reports_page.wait_for_spinner_to_end()

            self.reports_page.click_add_scheduling()
            assert self.reports_page.is_add_scheduling_selected()
