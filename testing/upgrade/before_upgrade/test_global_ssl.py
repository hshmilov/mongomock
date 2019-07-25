import os

from ui_tests.tests.ui_test_base import TestBase


class TestGlobalSSL(TestBase):
    def test_global_ssl(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        self.settings_page.open_global_ssl_toggle()
        keys_base_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                      '../../ssl_keys_for_tests'))

        crt_filename = os.path.join(keys_base_path, 'localhost.crt')
        cert_data = open(crt_filename, 'r').read()
        private_data = open(os.path.join(keys_base_path, 'localhost.key'), 'r').read()

        # Test that the right hostname works
        self.settings_page.set_global_ssl_settings('localhost', cert_data, private_data)
        self.settings_page.click_save_button()
        self.settings_page.wait_for_saved_successfully_toaster()
