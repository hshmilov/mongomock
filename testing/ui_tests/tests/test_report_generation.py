from datetime import datetime

from axonius.utils.wait import wait_until
from services.adapters import stresstest_scanner_service, stresstest_service
from ui_tests.pages.reports_page import ReportConfig
from ui_tests.tests import ui_consts
from ui_tests.tests.test_report_base import TestReportGenerationBase
from ui_tests.tests.ui_consts import MANAGED_DEVICES_QUERY_NAME


#pylint: disable=no-member
class TestReportGeneration(TestReportGenerationBase):
    def test_dashboard_data(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        with stress.contextmanager(take_ownership=True), stress_scanner.contextmanager(take_ownership=True):
            device_dict = {'device_count': 10, 'name': 'blah'}
            stress.add_client(device_dict)
            stress_scanner.add_client(device_dict)
            self.base_page.run_discovery()
            self.reports_page.create_report(ReportConfig(report_name=self.REPORT_NAME, add_dashboard=True))
            doc = self._extract_report_pdf_doc(self.REPORT_NAME)
            downloaded_doc = self._download_report_pdf_doc(self.REPORT_NAME)
            texts = [page.extractText() for page in doc.pages]
            text = ' '.join(texts)
            downloaded_texts = [page.extractText() for page in doc.pages]
            downloaded_text = ' '.join(texts)
            assert text == downloaded_text
            assert 'Device Discovery' in text
            assert 'User Discovery' in text
            self.adapters_page.clean_adapter_servers(ui_consts.STRESSTEST_ADAPTER_NAME)
            self.adapters_page.clean_adapter_servers(ui_consts.STRESSTEST_SCANNER_ADAPTER_NAME)
        self.wait_for_stress_adapter_down(ui_consts.STRESSTEST_ADAPTER)
        self.wait_for_stress_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def test_report_cover_and_toc_chart_legend(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        with stress.contextmanager(take_ownership=True), stress_scanner.contextmanager(take_ownership=True):
            device_dict = {'device_count': 10, 'name': 'blah'}
            stress.add_client(device_dict)
            stress_scanner.add_client(device_dict)

            self.base_page.run_discovery()

            report_name = 'report cover test'
            self.reports_page.create_report(ReportConfig(report_name=report_name, add_dashboard=True))

            doc = self._extract_report_pdf_doc(report_name)

            assert doc.pages[0].extractText().count(report_name) == 1
            assert doc.pages[0].extractText().count('Generated on') == 1

            toc_page = doc.pages[1]

            assert toc_page.extractText().count('Discovery Summary') == 1
            assert toc_page.extractText().count('Dashboard Charts') == 1
            assert toc_page.extractText().count('Saved Queries') == 0

            dashboard_chart_page = doc.pages[3]

            assert dashboard_chart_page.extractText().count(MANAGED_DEVICES_QUERY_NAME) == 2

            self.adapters_page.clean_adapter_servers(ui_consts.STRESSTEST_ADAPTER_NAME)
            self.adapters_page.clean_adapter_servers(ui_consts.STRESSTEST_SCANNER_ADAPTER_NAME)
        self.wait_for_stress_adapter_down(ui_consts.STRESSTEST_ADAPTER)
        self.wait_for_stress_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def test_multiple_reports_generated(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        with stress.contextmanager(take_ownership=True), stress_scanner.contextmanager(take_ownership=True):
            device_dict = {'device_count': 1000, 'name': 'blah'}
            stress.add_client(device_dict)
            stress_scanner.add_client(device_dict)

            self.reports_page.switch_to_page()

            self.base_page.run_discovery()

            self.devices_page.switch_to_page()

            self.devices_page.create_saved_query(self.DATA_QUERY, self.TEST_REPORT_QUERY_NAME)
            self.devices_page.create_saved_query(self.DATA_QUERY1, self.TEST_REPORT_QUERY_NAME1)
            self.devices_page.create_saved_query(self.DATA_QUERY2, self.TEST_REPORT_QUERY_NAME2)
            for i in range(0, 10):
                self.reports_page.create_report(ReportConfig(report_name=f'{self.REPORT_NAME}_{i}',
                                                             add_dashboard=True,
                                                             queries=[
                                                                 {
                                                                     'entity': 'Devices',
                                                                     'name': self.TEST_REPORT_QUERY_NAME
                                                                 },
                                                                 {
                                                                     'entity': 'Devices',
                                                                     'name': self.TEST_REPORT_QUERY_NAME1
                                                                 },
                                                                 {
                                                                     'entity': 'Devices',
                                                                     'name': self.TEST_REPORT_QUERY_NAME2
                                                                 }]))
                self.reports_page.wait_for_table_to_load()

            current_date = datetime.now()

            self.base_page.run_discovery()
            for i in range(0, 10):

                wait_until(lambda: self._new_generated_date(f'{self.REPORT_NAME}_{i}', current_date),
                           total_timeout=60 * 3, interval=2)

            self.adapters_page.clean_adapter_servers(ui_consts.STRESSTEST_ADAPTER_NAME)
            self.adapters_page.clean_adapter_servers(ui_consts.STRESSTEST_SCANNER_ADAPTER_NAME)
        self.wait_for_stress_adapter_down(ui_consts.STRESSTEST_ADAPTER)
        self.wait_for_stress_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def _new_generated_date(self, report_name, current_date):
        generated_date_str = self.reports_page.get_report_generated_date(report_name)
        if generated_date_str == '':
            return False
        generated_date = datetime.strptime(generated_date_str, '%Y-%m-%d %H:%M:%S')
        return generated_date > current_date
