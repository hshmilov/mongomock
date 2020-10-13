from services.standalone_services.syslog_service import SyslogService
from test_credentials.test_ad_credentials import ad_client1_details
from ui_tests.pages.page import TAB_BODY
from ui_tests.tests.ui_consts import EmailSettings, Saml, DISCOVERY_UPDATED_VALUE
from upgrade.UpgradeTestBase import UpgradeTestBase


class TestPrepareGlobalSettings(UpgradeTestBase):
    def test_email_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()

        self.settings_page.set_send_emails_toggle()

        self.settings_page.fill_email_host(EmailSettings.host)
        self.settings_page.fill_email_port(EmailSettings.port)
        self.settings_page.save_and_wait_for_toaster()

        self.settings_page.refresh()
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()

        assert self.settings_page.get_email_port() == EmailSettings.port
        assert self.settings_page.get_email_host() == EmailSettings.host

    def test_maintenance_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.toggle_advanced_settings()

        toggle = self.settings_page.find_remote_support_toggle()
        assert self.settings_page.is_toggle_selected(toggle)

        self.settings_page.set_remote_support_toggle(make_yes=False)

        self.settings_page.refresh()
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.toggle_advanced_settings()

        toggle = self.settings_page.find_remote_support_toggle()
        assert not self.settings_page.is_toggle_selected(toggle)

    def test_syslog_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()

        syslog_server = SyslogService()
        with syslog_server.contextmanager(take_ownership=True):
            self.settings_page.set_syslog_toggle(make_yes=True)
            self.settings_page.fill_syslog_host(syslog_server.name)
            self.settings_page.fill_syslog_port(syslog_server.tcp_port)
            self.settings_page.save_and_wait_for_toaster()

    def test_scheduler_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_lifecycle_settings()

        self.settings_page.click_toggle_button(self.settings_page.find_should_history_be_gathered_toggle(),
                                               make_yes=False)

        # change default discovery rate and verify value set post upgrade
        self.settings_page.fill_schedule_rate(DISCOVERY_UPDATED_VALUE)
        self.settings_page.save_and_wait_for_toaster()

    def test_gui_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_identity_providers_settings()
        self.settings_page.wait_for_spinner_to_end()

        toggle = self.settings_page.find_allow_ldap_logins_toggle()
        self.settings_page.click_toggle_button(toggle, window=TAB_BODY)
        self.settings_page.fill_dc_address(ad_client1_details['dc_name'])

        self.settings_page.click_save_identity_providers_settings()
        self.settings_page.wait_for_saved_successfully_toaster()

    def test_saml_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_identity_providers_settings()
        self.settings_page.wait_for_spinner_to_end()

        self.settings_page.set_allow_saml_based_login()
        self.settings_page.fill_saml_idp(Saml.idp)

        self.settings_page.upload_file_by_id(Saml.cert, Saml.cert_content)

        self.settings_page.save_and_wait_for_toaster()
