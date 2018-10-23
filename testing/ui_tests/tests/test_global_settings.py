from axonius.utils.wait import wait_until
from services.plugins.gui_service import GuiService
from services.standalone_services.smtp_server import SMTPService
from test_helpers.log_tester import LogTester
from ui_tests.tests.ui_test_base import TestBase

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

    def test_maintenance_endpoints(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        gui_service = GuiService()

        assert gui_service.troubleshooting().strip() == b'true'
        toggle = self.settings_page.find_remote_support_toggle()
        assert self.settings_page.is_toggle_selected(toggle)

        self.settings_page.set_remote_support_toggle(make_yes=False)
        self.settings_page.save_and_wait_for_toaster()
        wait_until(lambda: gui_service.troubleshooting().strip() == b'false')

        self.settings_page.set_remote_support_toggle(make_yes=True)
        self.settings_page.save_and_wait_for_toaster()
        wait_until(lambda: gui_service.troubleshooting().strip() == b'true')

    def test_remote_access_log(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.wait_for_spinner_to_end()

        self.settings_page.click_start_remote_access()
        wait_until(
            lambda: LogTester('../logs/gui/gui.axonius.log').is_pattern_in_log(
                '(Creating a stop job for the time|Job already existing - updating its run time to)', 10))
