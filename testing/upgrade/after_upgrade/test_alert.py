from ui_tests.pages.alert_page import Period, Trigger, Severity, Action
from ui_tests.tests.ui_consts import Alerts
from ui_tests.tests.ui_test_base import TestBase


class TestPrepareAlert(TestBase):

    def test_create_alert(self):
        self.alert_page.switch_to_page()
        self.alert_page.wait_for_spinner_to_end()
        self.alert_page.edit_alert(Alerts.alert_name_1)
        assert self.alert_page.is_period_selected(Period.Daily)  # Period
        assert self.alert_page.is_trigger_selected(Trigger.EveryDiscoveryCycle)  # Trigger
        assert self.alert_page.is_severity_selected(Severity.Warning)  # Severity
        assert self.alert_page.is_action_selected(Action.PushNotification)  # Action
