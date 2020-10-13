from upgrade.UpgradeTestBase import UpgradeTestBase


class TestDashboard(UpgradeTestBase):
    def test_new_dashboard(self):
        self.dashboard_page.switch_to_page()
        self.dashboard_page.wait_for_spinner_to_end()

        summary = self.dashboard_page.get_summary_card_text('test summary')
        summary.click()
