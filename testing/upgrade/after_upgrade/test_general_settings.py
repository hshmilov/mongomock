from services.standalone_services.syslog_server import SyslogService
from ui_tests.tests.ui_test_base import TestBase
from upgrade.consts import EmailSettings, FreshServiceSettings


class TestGeneralSettings(TestBase):
    def test_email_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()

        assert self.settings_page.get_email_port() == EmailSettings.port
        assert self.settings_page.get_email_host() == EmailSettings.host

    def test_maintenance_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()

        toggle = self.settings_page.find_remote_support_toggle()
        assert not self.settings_page.is_toggle_selected(toggle)

    def test_syslog_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()

        syslog_server = SyslogService()
        assert self.settings_page.is_toggle_selected(self.settings_page.find_syslog_toggle())
        assert self.settings_page.get_syslog_host() == syslog_server.name
        assert int(self.settings_page.get_syslog_port()) == syslog_server.port

    def test_fresh_service_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()

        assert self.settings_page.is_toggle_selected(self.settings_page.find_fresh_service_toggle())
        assert self.settings_page.get_fresh_service_domain() == FreshServiceSettings.domain
        assert self.settings_page.get_fresh_service_api_key() == FreshServiceSettings.apikey
        assert self.settings_page.get_fresh_service_email() == FreshServiceSettings.email

    def test_execution_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()

        assert self.settings_page.is_toggle_selected(self.settings_page.find_exection_toggle())
