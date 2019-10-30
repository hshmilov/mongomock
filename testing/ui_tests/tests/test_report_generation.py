import io
import urllib.parse
from functools import reduce
from datetime import datetime

from PyPDF2 import PdfFileReader

from services.adapters import stresstest_scanner_service, stresstest_service
from services.standalone_services.maildiranasaurus_server import MailDiranasaurusService
from services.standalone_services.smtp_server import generate_random_valid_email
from test_credentials.test_gui_credentials import DEFAULT_USER
from ui_tests.tests.ui_test_base import TestBase
from ui_tests.tests import ui_consts
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
    TEST_REPORT_SPACES = 'test report spaces'
    TEST_DASHBOARD_SPACE = 'test space'
    CUSTOM_SPACE_PANEL_NAME = 'Segment OS'

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
        try:
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
        finally:
            self.wait_for_adapter_down(ui_consts.STRESSTEST_ADAPTER)
            self.wait_for_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def test_saved_views_data_pdf_links(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        try:
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
        finally:
            self.wait_for_adapter_down(ui_consts.STRESSTEST_ADAPTER)
            self.wait_for_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def test_saved_views_data_device_no_dashboard_query(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        try:
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
        finally:
            self.wait_for_adapter_down(ui_consts.STRESSTEST_ADAPTER)
            self.wait_for_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def test_multiple_saved_queries(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        try:
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
        finally:
            self.wait_for_adapter_down(ui_consts.STRESSTEST_ADAPTER)
            self.wait_for_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def test_report_cover_and_toc_chart_legend(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        try:
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
        finally:
            self.wait_for_adapter_down(ui_consts.STRESSTEST_ADAPTER)
            self.wait_for_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def test_multiple_reports_generated(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        try:
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
                                                    queries=[{'entity': 'Devices',
                                                              'name': self.TEST_REPORT_QUERY_NAME},
                                                             {'entity': 'Devices',
                                                              'name': self.TEST_REPORT_QUERY_NAME1},
                                                             {'entity': 'Devices',
                                                              'name': self.TEST_REPORT_QUERY_NAME2}])
                    self.reports_page.wait_for_table_to_load()

                current_date = datetime.now()

                self.base_page.run_discovery()
                for i in range(0, 10):

                    wait_until(lambda: self._new_generated_date(f'{self.REPORT_NAME}_{i}', current_date),
                               total_timeout=60 * 3, interval=2)
        finally:
            self.wait_for_adapter_down(ui_consts.STRESSTEST_ADAPTER)
            self.wait_for_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def test_spaces_in_pdf(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        try:
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

                self.reports_page.create_report(report_name=self.TEST_REPORT_SPACES, add_dashboard=True,
                                                spaces=[self.TEST_DASHBOARD_SPACE])

                self.reports_page.click_report(self.TEST_REPORT_SPACES)
                self.reports_page.wait_for_spinner_to_end()
                assert self.reports_page.get_spaces()[0] == self.TEST_DASHBOARD_SPACE

                doc = self._extract_report_pdf_doc(self.TEST_REPORT_SPACES)
                texts = [page.extractText() for page in doc.pages]
                text = ' '.join(texts)
                assert self.TEST_REPORT_SPACES in text
        finally:
            self.wait_for_adapter_down(ui_consts.STRESSTEST_ADAPTER)
            self.wait_for_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def test_dashboard_data_with_trailing_space(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        try:
            with stress.contextmanager(take_ownership=True), stress_scanner.contextmanager(take_ownership=True):
                device_dict = {'device_count': 10, 'name': 'blah'}
                stress.add_client(device_dict)
                stress_scanner.add_client(device_dict)
                self.base_page.run_discovery()
                self.reports_page.create_report(report_name=self.REPORT_NAME + ' ', add_dashboard=True)
                doc = self._extract_report_pdf_doc(self.REPORT_NAME)
                texts = [page.extractText() for page in doc.pages]
                text = ' '.join(texts)
                assert 'Device Discovery' in text
                assert 'User Discovery' in text
        finally:
            self.wait_for_adapter_down(ui_consts.STRESSTEST_ADAPTER)
            self.wait_for_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def test_report_with_hebrew_name_and_text(self):
        smtp_service = MailDiranasaurusService()
        smtp_service.take_process_ownership()
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        try:
            with smtp_service.contextmanager(), \
                    stress.contextmanager(take_ownership=True), \
                    stress_scanner.contextmanager(take_ownership=True):
                device_dict = {'device_count': 10, 'name': 'blah'}
                stress.add_client(device_dict)
                stress_scanner.add_client(device_dict)
                self.base_page.run_discovery()

                self.settings_page.switch_to_page()
                self.settings_page.click_global_settings()
                toggle = self.settings_page.find_send_emails_toggle()
                self.settings_page.click_toggle_button(toggle, make_yes=True, scroll_to_toggle=False)
                self.settings_page.fill_email_host(smtp_service.fqdn)
                self.settings_page.fill_email_port(smtp_service.port)
                self.settings_page.save_and_wait_for_toaster()

                self.devices_page.switch_to_page()
                self.devices_page.wait_for_table_to_load()
                self.devices_page.click_row_checkbox()

                query_name = 'בדיקת שאילתא'
                self.devices_page.customize_view_and_save(query_name=query_name,
                                                          page_size=50,
                                                          sort_field=self.devices_page.FIELD_HOSTNAME_TITLE,
                                                          add_columns=[],
                                                          remove_columns=[self.devices_page.FIELD_LAST_SEEN,
                                                                          self.devices_page.FIELD_OS_TYPE,
                                                                          self.devices_page.FIELD_ASSET_NAME,
                                                                          self.devices_page.FIELD_HOSTNAME_TITLE],
                                                          query_filter=self.devices_page.STRESSTEST_ADAPTER_FILTER)
                self.devices_page.click_row_checkbox()
                tag_name = 'טאג בעברית'
                self.devices_page.add_new_tag(tag_name)
                report_name = 'בדיקה'
                recipient = generate_random_valid_email()
                self.reports_page.create_report(report_name=report_name,
                                                add_dashboard=True,
                                                queries=[{'entity': 'Devices', 'name': query_name}],
                                                add_scheduling=True,
                                                email_subject=report_name,
                                                emails=[recipient])
                doc = self._extract_report_pdf_doc(report_name)
                texts = [page.extractText() for page in doc.pages]
                text = ' '.join(texts)
                assert 'Device Discovery' in text
                assert 'User Discovery' in text

                title_texts = self._get_outline_titles(doc.getOutlines())

                assert query_name in title_texts

                self.reports_page.click_send_email()
                self.reports_page.find_email_sent_toaster()
                mail_content = smtp_service.get_email_first_csv_content(recipient)
                assert tag_name in mail_content.decode('utf-8')
                self.logger.info('We are done with test_report_with_hebrew_name_and_text test')
        finally:
            self.wait_for_adapter_down(ui_consts.STRESSTEST_ADAPTER)
            self.wait_for_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def _new_generated_date(self, report_name, current_date):
        generated_date_str = self.reports_page.get_report_generated_date(report_name)
        if generated_date_str == '':
            return False
        generated_date = datetime.strptime(generated_date_str, '%Y-%m-%d %H:%M:%S')
        return generated_date > current_date

    def _extract_report_pdf_doc(self, report_name):
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        report_id = self.reports_page.get_report_id(report_name)
        self.reports_page.wait_for_report_generation(report_name)
        self.reports_page.click_report(report_name)
        self.reports_page.wait_for_spinner_to_end()
        self.axonius_system.gui.login_user(DEFAULT_USER)
        report_pdf = self.axonius_system.gui.get_report_pdf(report_id)
        pdf_file = io.BytesIO(report_pdf.content)
        return PdfFileReader(pdf_file)

    def _get_outline_titles(self, outlines):
        outline_titles = []
        for outline in outlines:
            if not isinstance(outline, list):
                outline_titles.append(str(outline.title))
            else:
                for inner_outline in self._get_outline_titles(outline):
                    outline_titles.append(inner_outline)
        return outline_titles
