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

            doc = self._enter_and_get_report_pdf_doc_from_endpoint(self.TEST_REPORT_SPACES)
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

            self._test_report_pdf_with_query(self.REPORT_NAME, self.DATA_QUERY, self.TEST_REPORT_QUERY_NAME)
            self._test_report_pdf_with_query(self.REPORT_NAME1, self.DATA_QUERY1, self.TEST_REPORT_QUERY_NAME1,
                                             add_col_names=[self.devices_page.FIELD_FIRST_FETCH_TIME],
                                             remove_col_names=[self.devices_page.FIELD_OS_TYPE,
                                                               self.devices_page.FIELD_LAST_SEEN,
                                                               self.devices_page.FIELD_TAGS])

            self.adapters_page.clean_adapter_servers(ui_consts.STRESSTEST_ADAPTER_NAME)
            self.adapters_page.clean_adapter_servers(ui_consts.STRESSTEST_SCANNER_ADAPTER_NAME)
        self.wait_for_stress_adapter_down(ui_consts.STRESSTEST_ADAPTER)
        self.wait_for_stress_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def _test_report_pdf_with_query(self, report_name, data_query, query_name,
                                    add_col_names=None, remove_col_names=None):
        self.devices_page.create_saved_query(data_query, query_name,
                                             add_col_names=add_col_names, remove_col_names=remove_col_names)
        self.devices_page.wait_for_table_to_be_responsive()
        headers = ''.join(self.devices_page.get_columns_header_text()[:6]).replace(' ', '')
        self.reports_page.create_report(ReportConfig(report_name=report_name, add_dashboard=True,
                                                     queries=[{
                                                         'entity': 'Devices',
                                                         'name': query_name}]))
        doc = self._enter_and_get_report_pdf_doc_from_endpoint(report_name)
        annots = [page.get('/Annots', []) for page in doc.pages]
        annots = reduce(lambda x, y: x + y, annots)
        links = [note.get('/A', {}).get('/URI') for note in annots]
        assert len(links) > 0
        decoded_links = map(urllib.parse.unquote, links)
        assert any(query_name in link for link in decoded_links)
        for page in doc.pages:
            page_text = page.extractText()
            if query_name in page_text:
                assert page_text.count('avigdor') == 10
                assert headers in page_text.replace('\n', ' ').replace('\r', '').replace(' ', '')

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

            doc = self._enter_and_get_report_pdf_doc_from_endpoint(self.REPORT_NAME)
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
