import time

from ui_tests.pages.enforcements_page import Period
from ui_tests.tests.ui_consts import Enforcements
from upgrade.UpgradeTestBase import UpgradeTestBase


class TestEnforcement(UpgradeTestBase):
    def test_create_enforcement(self):
        self.enforcements_page.switch_to_page()
        self.enforcements_page.wait_for_table_to_load()
        self.enforcements_page.click_enforcement(Enforcements.enforcement_name_1)

        # AX-3772
        time.sleep(2)

        self.enforcements_page.select_trigger()
        assert self.enforcements_page.is_period_selected(Period.Daily)  # Period
        assert self.enforcements_page.is_action_selected('Special Push Notification')  # Action
