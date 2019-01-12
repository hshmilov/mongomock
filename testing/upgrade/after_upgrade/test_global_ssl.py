from ui_tests.tests.ui_consts import TEMP_FILE_PREFIX
from ui_tests.tests.ui_test_base import TestBase


class TestGlobalSSL(TestBase):
    def test_global_ssl(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        cert_file, private_key = self.settings_page.get_global_ssl_settings()
        assert cert_file.startswith(TEMP_FILE_PREFIX)
        assert private_key.startswith(TEMP_FILE_PREFIX)
