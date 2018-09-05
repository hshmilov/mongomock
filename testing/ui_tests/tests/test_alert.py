from ui_tests.tests.ui_test_base import TestBase


class TestAlert(TestBase):
    def test_new_alert_no_email_server(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_send_emails_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=False)
        self.settings_page.click_save_button()

        self.alert_page.switch_to_page()
        self.alert_page.click_new_alert()
        self.alert_page.fill_alert_name('Alert name')
        self.alert_page.wait_for_spinner_to_end()
        self.alert_page.click_send_an_email()
        self.alert_page.find_missing_email_server_notification()
