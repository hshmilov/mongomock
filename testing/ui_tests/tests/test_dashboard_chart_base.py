import time

from ui_tests.tests.ui_test_base import TestBase


class TestDashboardChartBase(TestBase):

    def _download_and_get_csv(self, card_title):
        self.dashboard_page.export_card(card_title)
        time.sleep(1)  # wait for the file to be downloaded
        csv_file_name = f'axonius-chart-{card_title}'
        downloaded_csv = self.get_downloaded_file_content(csv_file_name, 'csv')
        all_csv_rows = downloaded_csv.decode('utf-8').split('\r\n')
        return [x.split(',') for x in all_csv_rows[1:-1]]
