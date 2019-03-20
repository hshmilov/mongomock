import time

from ui_tests.pages.enforcements_page import Period
from ui_tests.tests.ui_consts import Enforcements
from ui_tests.tests.ui_test_base import TestBase


class TestPrepareEnforcement(TestBase):
    def test_create_enforcement(self):
        self.enforcements_page.create_basic_enforcement(Enforcements.enforcement_name_1,
                                                        Enforcements.enforcement_query_1)

        self.enforcements_page.select_trigger()
        # Sometimes the page triggers are rendered too slow and it caused us to click another element (label)
        time.sleep(2)
        self.enforcements_page.choose_period(Period.Daily)  # Period
        self.enforcements_page.save_trigger()
        self.enforcements_page.add_push_system_notification()  # Action

        self.enforcements_page.click_save_button()
        self.enforcements_page.wait_for_table_to_load()
