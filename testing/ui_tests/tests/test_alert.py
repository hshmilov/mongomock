from ui_tests.tests.ui_test_base import TestBase

ALERT_NAME = 'Special alert name'


class TestAlert(TestBase):
    def test_new_alert_no_email_server(self):
        self.settings_page.switch_to_page()
        self.settings_page.click_global_settings()
        toggle = self.settings_page.find_send_emails_toggle()
        self.settings_page.click_toggle_button(toggle, make_yes=False)
        self.settings_page.click_save_button()

        self.alert_page.switch_to_page()
        self.alert_page.click_new_alert()
        self.alert_page.fill_alert_name(ALERT_NAME)
        self.alert_page.wait_for_spinner_to_end()
        self.alert_page.click_send_an_email()
        self.alert_page.find_missing_email_server_notification()

    def test_remove_alert(self):
        self.create_outputting_notification_alert()

        self.base_page.run_discovery()
        assert self.notification_page.is_text_in_peek_notifications(ALERT_NAME)
        old_length = len(self.notification_page.get_peek_notifications())

        self.alert_page.switch_to_page()
        self.alert_page.wait_for_spinner_to_end()
        self.alert_page.select_all_alerts()
        self.alert_page.remove_selected_alerts()

        self.base_page.run_discovery()
        new_length = len(self.notification_page.get_peek_notifications())

        assert old_length == new_length

    def create_outputting_notification_alert(self):
        self.alert_page.switch_to_page()
        self.alert_page.click_new_alert()
        self.alert_page.wait_for_spinner_to_end()
        self.alert_page.fill_alert_name(ALERT_NAME)
        self.alert_page.select_saved_query('Enabled AD Devices')
        self.alert_page.check_increased()
        self.alert_page.check_decreased()
        self.alert_page.check_not_changed()
        self.alert_page.check_push_system_notification()
        self.alert_page.click_save_button()
