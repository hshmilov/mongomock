from services.standalone_services.syslog_server import SyslogService
from test_credentials.test_ad_credentials import ad_client1_details
from test_credentials.test_okta_credentials import OKTA_LOGIN_DETAILS
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.ui_consts import EmailSettings, Saml, TEMP_FILE_PREFIX


class TestGeneralSettings(TestBase):
    def test_email_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.wait_for_spinner_to_end()

        assert self.settings_page.get_email_port() == EmailSettings.port
        assert self.settings_page.get_email_host() == EmailSettings.host

    def test_maintenance_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.toggle_advanced_settings()

        toggle = self.settings_page.find_remote_support_toggle()
        assert not self.settings_page.is_toggle_selected(toggle)
        toggle = self.settings_page.find_analytics_toggle()
        assert self.settings_page.is_toggle_selected(toggle)

    def test_syslog_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.wait_for_spinner_to_end()

        syslog_server = SyslogService()
        assert self.settings_page.is_toggle_selected(self.settings_page.find_syslog_toggle())
        assert self.settings_page.get_syslog_host() == syslog_server.name
        assert int(self.settings_page.get_syslog_port()) == syslog_server.tcp_port

    def test_scheduler_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_lifecycle_settings()
        self.settings_page.wait_for_spinner_to_end()

        assert self.settings_page.is_toggle_selected(
            self.settings_page.find_should_history_be_gathered_toggle()) is False

    def test_gui_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_gui_settings()
        self.settings_page.wait_for_spinner_to_end()

        assert self.settings_page.get_single_adapter_checkbox()
        assert self.settings_page.get_okta_login_details() == OKTA_LOGIN_DETAILS

        assert self.settings_page.get_dc_address() == ad_client1_details['dc_name']

    def test_saml_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_gui_settings()
        self.settings_page.wait_for_spinner_to_end()

        assert self.settings_page.is_saml_login_enabled()
        assert self.settings_page.get_saml_idp() == Saml.idp
        assert self.settings_page.get_filename_by_input_id(Saml.cert).startswith(TEMP_FILE_PREFIX)
        # note: move saml_login_settings->const
        uuid = self.axonius_system.gui.get_saml_settings()['saml_login_settings'][Saml.cert]['uuid']
        assert self.axonius_system.gui.get_file_content_from_db(uuid).decode() == Saml.cert_content
