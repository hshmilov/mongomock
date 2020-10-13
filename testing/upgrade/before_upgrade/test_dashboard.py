from upgrade.UpgradeTestBase import UpgradeTestBase


class TestNotes(UpgradeTestBase):
    def test_new_dashboard(self):
        self.dashboard_page.switch_to_page()
        self.dashboard_page.wait_for_spinner_to_end()

        self.dashboard_page.add_summary_card('Devices', 'Host Name', 'Count', 'test summary')
