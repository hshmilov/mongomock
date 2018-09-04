import time

from ui_tests.tests.ui_test_base import TestBase
from upgrade.consts import EmailSettings


class TestPrepareGlobalSettings(TestBase):
    def test_email_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()

        time.sleep(1)  # https://axonius.atlassian.net/browse/AX-1992
        self.settings_page.set_send_emails_toggle()

        self.settings_page.fill_email_host(EmailSettings.host)
        self.settings_page.fill_email_port(EmailSettings.port)
        self.settings_page.click_save_button()
        self.settings_page.wait_for_toaster('Saved Successfully.')

        self.settings_page.refresh()
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()

        assert self.settings_page.get_email_port() == EmailSettings.port
        assert self.settings_page.get_email_host() == EmailSettings.host
