from ui_tests.tests.ui_test_base import TestBase
from upgrade.consts import EmailSettings


class TestGeneralSettings(TestBase):
    def test_email_settings(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()

        assert self.settings_page.get_email_port() == EmailSettings.port
        assert self.settings_page.get_email_host() == EmailSettings.host
