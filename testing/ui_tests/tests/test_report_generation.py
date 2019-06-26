import io
import urllib.parse
from functools import reduce
from datetime import datetime

from PyPDF2 import PdfFileReader

from services.adapters import stresstest_scanner_service, stresstest_service
from test_credentials.test_gui_credentials import DEFAULT_USER
from ui_tests.tests.ui_test_base import TestBase
from axonius.utils.wait import wait_until


class TestReportGeneration(TestBase):
    REPORT_NAME = 'test_report_gen'
    EMPTY_REPORT_NAME = 'empty_report'
    TEST_REPORT_QUERY_NAME = 'test report query name'
    TEST_REPORT_QUERY_NAME1 = 'test report query name1'
    TEST_REPORT_QUERY_NAME2 = 'test report query name2'
    DATA_QUERY = 'specific_data.data.name == regex(\'avigdor no\', \'i\')'
    DATA_QUERY1 = 'specific_data.data.name == regex(\'avigdor\', \'i\')'
    DATA_QUERY2 = 'specific_data.data.name == regex(\'avig\', \'i\')'

    def test_empty_report(self):
        self.reports_page.create_report(report_name=self.EMPTY_REPORT_NAME)

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
            self.reports_page.create_report(report_name=self.REPORT_NAME, add_dashboard=True)
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
            self.devices_page.create_saved_query(data_query, self.TEST_REPORT_QUERY_NAME)
            self.devices_page.wait_for_table_to_load()
            self.reports_page.create_report(report_name=self.REPORT_NAME, add_dashboard=True,
                                            queries=[{'entity': 'Devices', 'name': self.TEST_REPORT_QUERY_NAME}])

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

    def test_saved_views_data_device_no_dashboard_query(self):
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

            self.reports_page.create_report(report_name=self.REPORT_NAME, add_dashboard=False,
                                            queries=[{'entity': 'Devices', 'name': self.TEST_REPORT_QUERY_NAME}])

            doc = self._extract_report_pdf_doc(self.REPORT_NAME)
            texts = [page.extractText() for page in doc.pages]
            text = ' '.join(texts)
            assert 'Devices - Saved Queries' in text
            assert 'Users - Saved Queries' not in text
            assert 'top 10 results of 10' in text
            assert 'Device Discovery' not in text
            assert 'User Discovery' not in text

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
            self.reports_page.create_report(report_name=self.REPORT_NAME, add_dashboard=False,
                                            queries=[{'entity': 'Devices', 'name': self.TEST_REPORT_QUERY_NAME},
                                                     {'entity': 'Devices', 'name': self.TEST_REPORT_QUERY_NAME2}])

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

    def test_report_cover_and_toc_chart_legend(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        with stress.contextmanager(take_ownership=True), stress_scanner.contextmanager(take_ownership=True):
            device_dict = {'device_count': 10, 'name': 'blah'}
            stress.add_client(device_dict)
            stress_scanner.add_client(device_dict)

            self.base_page.run_discovery()

            report_name = 'report cover test'
            self.reports_page.create_report(report_name=report_name, add_dashboard=True)

            doc = self._extract_report_pdf_doc(report_name)

            assert doc.pages[0].extractText().count(report_name) == 1
            assert doc.pages[0].extractText().count('Generated on') == 1

            toc_page = doc.pages[1]

            assert toc_page.extractText().count('Discovery Summary') == 1
            assert toc_page.extractText().count('Dashboard Charts') == 1
            assert toc_page.extractText().count('Saved Queries') == 0

            dashboard_chart_page = doc.pages[3]

            assert dashboard_chart_page.extractText().count('Managed Devices') == 2

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
                self.reports_page.create_report(report_name=f'{self.REPORT_NAME}_{i}', add_dashboard=True,
                                                queries=[{'entity': 'Devices', 'name': self.TEST_REPORT_QUERY_NAME},
                                                         {'entity': 'Devices', 'name': self.TEST_REPORT_QUERY_NAME1},
                                                         {'entity': 'Devices', 'name': self.TEST_REPORT_QUERY_NAME2}])
                self.reports_page.wait_for_table_to_load()

            current_date = datetime.now()

            self.base_page.run_discovery()
            for i in range(0, 10):

                wait_until(lambda: self._new_generated_date(f'{self.REPORT_NAME}_{i}', current_date),
                           total_timeout=60 * 3, interval=2)

    def _new_generated_date(self, report_name, current_date):
        generated_date_str = self.reports_page.get_report_generated_date(report_name)
        if generated_date_str == '':
            return False
        generated_date = datetime.strptime(generated_date_str, '%Y-%m-%d %H:%M:%S')
        return generated_date > current_date

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
