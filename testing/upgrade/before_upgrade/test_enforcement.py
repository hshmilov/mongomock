from ui_tests.pages.enforcements_page import Period
from ui_tests.tests.ui_consts import Enforcements
from ui_tests.tests.ui_test_base import TestBase


class TestPrepareEnforcement(TestBase):
    def test_create_enforcement(self):
        self.devices_page.create_saved_query(self.devices_page.FILTER_OS_WINDOWS, Enforcements.enforcement_query_1)
        self.enforcements_page.create_basic_enforcement(Enforcements.enforcement_name_1)
        self.enforcements_page.add_push_system_notification()  # Action
        self.enforcements_page.create_trigger(Enforcements.enforcement_query_1, save=False)
        self.enforcements_page.choose_period(Period.Daily)  # Period
        self.enforcements_page.click_save_button()
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_be_responsive()
