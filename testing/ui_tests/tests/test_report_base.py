import io

from PyPDF2 import PdfFileReader

from test_credentials.test_gui_credentials import DEFAULT_USER
from ui_tests.tests.ui_test_base import TestBase


class TestReportGenerationBase(TestBase):
    REPORT_NAME = 'test_report_gen'
    REPORT_NAME1 = 'test_report_gen1'
    TEST_REPORT_QUERY_NAME = 'test report query name'
    DATA_QUERY = 'specific_data.data.name == regex(\'avigdor no\', \'i\')'
    DATA_QUERY1 = 'specific_data.data.name == regex(\'avigdor\', \'i\')'
    DATA_QUERY2 = 'specific_data.data.name == regex(\'avig\', \'i\')'
    TEST_REPORT_QUERY_NAME1 = 'test report query name1'
    TEST_REPORT_QUERY_NAME2 = 'test report query name2'

    def _enter_and_get_report_pdf_doc_from_endpoint(self, report_name):
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_be_responsive()
        report_id = self.reports_page.get_report_id(report_name)
        self.reports_page.wait_for_report_generation(report_name)
        self.reports_page.click_report(report_name)
        self.reports_page.wait_for_spinner_to_end()
        self.axonius_system.gui.login_user(DEFAULT_USER)
        report_pdf = self.axonius_system.gui.get_report_pdf(report_id)
        pdf_file = io.BytesIO(report_pdf.content)
        return PdfFileReader(pdf_file)

    def _download_report_pdf_doc(self, report_name):
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_be_responsive()
        self.reports_page.wait_for_report_generation(report_name)
        self.reports_page.click_report(report_name)
        self.reports_page.wait_for_spinner_to_end()
        self.reports_page.click_report_download()

        report = self.get_downloaded_file_content(report_name.replace(' ', '_'), 'pdf')
        pdf_file = io.BytesIO(report)
        return PdfFileReader(pdf_file)
