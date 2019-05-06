import io
import urllib.parse
from functools import reduce

from PyPDF2 import PdfFileReader

from services.adapters import stresstest_scanner_service, stresstest_service
from test_credentials.test_gui_credentials import DEFAULT_USER
from ui_tests.tests.ui_test_base import TestBase


class TestReportGeneration(TestBase):
    REPORT_NAME = 'test_report_gen'
    EMPTY_REPORT_NAME = 'empty_report'
    TEST_REPORT_QUERY_NAME = 'test report query name'
    DATA_QUERY = 'specific_data.data.name == regex(\'avigdor no\', \'i\')'

    def test_empty_report(self):
        self.reports_page.create_report(self.EMPTY_REPORT_NAME)

        report_name = self.EMPTY_REPORT_NAME

        doc = self._extract_report_pdf_doc(report_name)
        texts = [page.extractText() for page in doc.pages]
        text = ' '.join(texts)
        assert 'Device Discovery' not in text
        assert 'User Discovery' not in text

    def test_dashboard_data(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        with stress.contextmanager(take_ownership=True), stress_scanner.contextmanager(take_ownership=True):
            device_dict = {'device_count': 10, 'name': 'blah'}
            stress.add_client(device_dict)
            stress_scanner.add_client(device_dict)
            self.base_page.run_discovery()
            self.reports_page.create_report(self.REPORT_NAME, True)
            doc = self._extract_report_pdf_doc(self.REPORT_NAME)
            texts = [page.extractText() for page in doc.pages]
            text = ' '.join(texts)
            assert 'Device Discovery' in text
            assert 'User Discovery' in text

    def test_saved_views_data_pdf_links(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        with stress.contextmanager(take_ownership=True), stress_scanner.contextmanager(take_ownership=True):
            device_dict = {'device_count': 10, 'name': 'blah'}
            stress.add_client(device_dict)
            stress_scanner.add_client(device_dict)

            self.base_page.run_discovery()

            data_query = self.DATA_QUERY
            self.devices_page.switch_to_page()
            self.devices_page.fill_filter(data_query)
            self.devices_page.enter_search()
            self.devices_page.open_edit_columns()
            self.devices_page.select_column_name(self.devices_page.FIELD_NETWORK_INTERFACES_MAC)
            self.devices_page.close_edit_columns()
            self.devices_page.wait_for_table_to_load()
            self.devices_page.click_sort_column(self.devices_page.FIELD_ASSET_NAME)
            self.devices_page.click_save_query()
            self.devices_page.fill_query_name(self.TEST_REPORT_QUERY_NAME)
            self.devices_page.click_save_query_save_button()

            self.reports_page.create_report(self.REPORT_NAME, True, self.TEST_REPORT_QUERY_NAME)

            doc = self._extract_report_pdf_doc(self.REPORT_NAME)
            annots = [page.get('/Annots', []) for page in doc.pages]
            annots = reduce(lambda x, y: x + y, annots)
            links = [note.get('/A', {}).get('/URI') for note in annots]
            assert len(links) > 0

            decoded_links = map(urllib.parse.unquote, links)
            assert any(self.TEST_REPORT_QUERY_NAME in link for link in decoded_links)

            third_page = doc.pages[2]
            assert third_page.extractText().count('avigdor') == 10

    def _extract_report_pdf_doc(self, report_name):
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        self.reports_page.wait_for_report_generation(report_name)
        self.reports_page.click_report(report_name)
        self.reports_page.wait_for_spinner_to_end()
        self.axonius_system.gui.login_user(DEFAULT_USER)
        report_pdf = self.axonius_system.gui.get_report_pdf(report_name)
        pdf_file = io.BytesIO(report_pdf.content)
        return PdfFileReader(pdf_file)
