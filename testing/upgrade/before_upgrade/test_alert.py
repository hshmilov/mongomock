from ui_tests.pages.alert_page import Period
from ui_tests.tests.ui_consts import Alerts
from ui_tests.tests.ui_test_base import TestBase


class TestPrepareAlert(TestBase):
    def test_create_alert(self):
        self.alert_page.create_basic_alert(Alerts.alert_name_1, Alerts.alert_query_1)

        self.alert_page.choose_period(Period.Daily)  # Period
        self.alert_page.choose_severity_warning()  # Severity
        self.alert_page.check_every_discovery()  # Trigger
        self.alert_page.check_push_system_notification()  # Action

        self.alert_page.click_save_button()
        self.alert_page.wait_for_spinner_to_end()
