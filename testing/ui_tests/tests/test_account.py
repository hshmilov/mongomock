from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests.test_api import get_device_views_from_api


class TestAccount(TestBase):
    def check_secret_api_key_invisible(self):
        num_of_char_in_secret_key = len(self.account_page.get_visible_secret_key_field_value())
        assert '*' * num_of_char_in_secret_key == self.account_page.get_masked_secret_key_field_value()

    def test_set_secret_api_key_visible(self):
        self.account_page.switch_to_page()
        self.account_page.wait_for_spinner_to_end()
        account_data = self.account_page.get_api_key_and_secret()
        assert get_device_views_from_api(account_data).status_code == 200
        self.check_secret_api_key_invisible()
        assert self.account_page.is_set_secret_key_visisble_icon()
        assert not self.account_page.is_key_secret_displayed()
        assert self.account_page.is_key_mask_displayed()
        self.account_page.click_show_secret_api_key_button()
        assert self.account_page.is_set_secret_key_invisisble_icon()
        assert self.account_page.is_key_secret_displayed()
        assert not self.account_page.is_key_mask_displayed()

    def test_secret_key_copied_to_clipboard(self):
        self.account_page.switch_to_page()
        self.account_page.wait_for_spinner_to_end()
        self.account_page.click_copy_to_clipboard()
        self.account_page.wait_for_toaster('Key was copied to Clipboard')
