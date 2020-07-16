import urllib.parse
from functools import reduce

from services.adapters import stresstest_service, stresstest_scanner_service
from ui_tests.pages.reports_page import ReportConfig
from ui_tests.tests import ui_consts
from ui_tests.tests.test_report_base import TestReportGenerationBase


class TestReportGenerationMoreCases(TestReportGenerationBase):
    TEST_DASHBOARD_SPACE = 'test space'
    CUSTOM_SPACE_PANEL_NAME = 'Segment OS'
    TEST_REPORT_SPACES = 'test report spaces'

    def test_spaces_in_pdf(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        with stress.contextmanager(take_ownership=True), stress_scanner.contextmanager(
                take_ownership=True):
            device_dict = {'device_count': 10, 'name': 'blah'}
            stress.add_client(device_dict)
            stress_scanner.add_client(device_dict)
            self.dashboard_page.switch_to_page()

            self.base_page.run_discovery()
            self.dashboard_page.refresh()

            # Add new space and name it
            self.dashboard_page.add_new_space(self.TEST_DASHBOARD_SPACE)
            self.dashboard_page.find_space_header(3).click()
            self.dashboard_page.add_segmentation_card('Devices', 'OS: Type', self.CUSTOM_SPACE_PANEL_NAME)

            self._test_reports_dashboard_placeholder()
            self.reports_page.create_report(ReportConfig(report_name=self.TEST_REPORT_SPACES, add_dashboard=True,
                                                         spaces=[self.TEST_DASHBOARD_SPACE]))

            self.reports_page.click_report(self.TEST_REPORT_SPACES)
            self.reports_page.wait_for_spinner_to_end()
            assert self.reports_page.get_space_select_selected_options()[0] == self.TEST_DASHBOARD_SPACE

            doc = self._extract_report_pdf_doc(self.TEST_REPORT_SPACES)
            texts = [page.extractText() for page in doc.pages]
            text = ' '.join(texts)
            assert self.TEST_REPORT_SPACES in text

            self.adapters_page.clean_adapter_servers(ui_consts.STRESSTEST_ADAPTER_NAME)
            self.adapters_page.clean_adapter_servers(ui_consts.STRESSTEST_SCANNER_ADAPTER_NAME)
        self.wait_for_stress_adapter_down(ui_consts.STRESSTEST_ADAPTER)
        self.wait_for_stress_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def test_saved_views_data_pdf_links(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        with stress.contextmanager(take_ownership=True), stress_scanner.contextmanager(take_ownership=True):
            device_dict = {'device_count': 10, 'name': 'blah'}
            stress.add_client(device_dict)
            stress_scanner.add_client(device_dict)

            self.base_page.run_discovery()

            data_query = self.DATA_QUERY
            self.devices_page.create_saved_query(data_query, self.TEST_REPORT_QUERY_NAME)
            self.devices_page.wait_for_table_to_load()
            self.reports_page.create_report(ReportConfig(report_name=self.REPORT_NAME, add_dashboard=True,
                                                         queries=[{
                                                             'entity': 'Devices',
                                                             'name': self.TEST_REPORT_QUERY_NAME}]))

            doc = self._extract_report_pdf_doc(self.REPORT_NAME)
            annots = [page.get('/Annots', []) for page in doc.pages]
            annots = reduce(lambda x, y: x + y, annots)
            links = [note.get('/A', {}).get('/URI') for note in annots]
            assert len(links) > 0

            decoded_links = map(urllib.parse.unquote, links)
            assert any(self.TEST_REPORT_QUERY_NAME in link for link in decoded_links)
            for page in doc.pages:
                if page.extractText().count('self.TEST_REPORT_QUERY_NAME') > 0:
                    assert page.extractText().count('avigdor') == 10

            self.adapters_page.clean_adapter_servers(ui_consts.STRESSTEST_ADAPTER_NAME)
            self.adapters_page.clean_adapter_servers(ui_consts.STRESSTEST_SCANNER_ADAPTER_NAME)
        self.wait_for_stress_adapter_down(ui_consts.STRESSTEST_ADAPTER)
        self.wait_for_stress_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def test_multiple_saved_queries(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        with stress.contextmanager(take_ownership=True), stress_scanner.contextmanager(take_ownership=True):
            device_dict = {'device_count': 10, 'name': 'blah'}
            stress.add_client(device_dict)
            stress_scanner.add_client(device_dict)
            self.base_page.run_discovery()
            self.devices_page.create_saved_query(self.DATA_QUERY, self.TEST_REPORT_QUERY_NAME)
            self.devices_page.create_saved_query(self.DATA_QUERY1, self.TEST_REPORT_QUERY_NAME1)
            self.devices_page.create_saved_query(self.DATA_QUERY2, self.TEST_REPORT_QUERY_NAME2)
            self.reports_page.create_report(ReportConfig(report_name=self.REPORT_NAME, add_dashboard=False,
                                                         queries=[
                                                             {
                                                                 'entity': 'Devices',
                                                                 'name': self.TEST_REPORT_QUERY_NAME
                                                             },
                                                             {
                                                                 'entity': 'Devices',
                                                                 'name': self.TEST_REPORT_QUERY_NAME2
                                                             }]))

            doc = self._extract_report_pdf_doc(self.REPORT_NAME)
            texts = [page.extractText() for page in doc.pages]
            text = ' '.join(texts)
            assert 'Devices - Saved Queries' in text
            assert 'Users - Saved Queries' not in text
            assert 'top 10 results of 10' in text
            assert 'Device Discovery' not in text
            assert 'User Discovery' not in text

            assert self.TEST_REPORT_QUERY_NAME in text
            assert self.TEST_REPORT_QUERY_NAME1 not in text
            assert self.TEST_REPORT_QUERY_NAME2 in text

            self.adapters_page.clean_adapter_servers(ui_consts.STRESSTEST_ADAPTER_NAME)
            self.adapters_page.clean_adapter_servers(ui_consts.STRESSTEST_SCANNER_ADAPTER_NAME)
        self.wait_for_stress_adapter_down(ui_consts.STRESSTEST_ADAPTER)
        self.wait_for_stress_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def _test_reports_dashboard_placeholder(self):
        self.reports_page.switch_to_page()
        self.reports_page.click_new_report()

        self.reports_page.click_include_dashboard()
        self.reports_page.wait_for_spaces_select_help_message()
