from ui_tests.tests.test_dashboard_chart_base import TestDashboardChartBase


class TestNewChartStress(TestDashboardChartBase):

    def test_new_chart_stress(self):
        self.dashboard_page.switch_to_page()
        self.base_page.run_discovery()
        for i in range(10):
            self.dashboard_page.add_summary_card('Devices', 'Host Name', 'Count',
                                                 f'{self.TEST_SUMMARY_TITLE_DEVICES}{i}')
            self.dashboard_page.wait_for_spinner_to_end()
            self.dashboard_page.get_card(f'{self.TEST_SUMMARY_TITLE_DEVICES}{i}')
        last_card = self.dashboard_page.get_all_cards()[-1]
        assert self.dashboard_page.get_title_from_card(last_card) == 'New Chart'
        for j in range(10):
            self.dashboard_page.remove_card(f'{self.TEST_SUMMARY_TITLE_DEVICES}{j}')
            self.dashboard_page.wait_for_spinner_to_end()
