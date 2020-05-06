from selenium.common.exceptions import StaleElementReferenceException

from axonius.utils.wait import wait_until
from services.adapters import stresstest_scanner_service, stresstest_service
from services.standalone_services.maildiranasaurus_service import \
    MaildiranasaurusService
from services.standalone_services.smtp_service import \
    generate_random_valid_email
from ui_tests.pages.reports_page import ReportConfig
from ui_tests.tests import ui_consts
from ui_tests.tests.test_report_base import TestReportGenerationBase
from ui_tests.tests.ui_consts import MANAGED_DEVICES_QUERY_NAME

# pylint: disable=E1101


#pylint: disable=no-member
class TestReportGenerationSpecialCases(TestReportGenerationBase):
    EMPTY_REPORT_NAME = 'empty_report'

    def test_empty_report(self):
        self.reports_page.create_report(ReportConfig(report_name=self.EMPTY_REPORT_NAME))

        report_name = self.EMPTY_REPORT_NAME

        doc = self._extract_report_pdf_doc(report_name)
        texts = [page.extractText() for page in doc.pages]
        text = ' '.join(texts)
        assert 'Device Discovery' not in text
        assert 'User Discovery' not in text

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

            self.reports_page.create_report(ReportConfig(report_name=self.REPORT_NAME, add_dashboard=False,
                                                         queries=[{
                                                             'entity': 'Devices',
                                                             'name': self.TEST_REPORT_QUERY_NAME
                                                         }]))

            doc = self._extract_report_pdf_doc(self.REPORT_NAME)
            texts = [page.extractText() for page in doc.pages]
            text = ' '.join(texts)
            assert 'Devices - Saved Queries' in text
            assert 'Users - Saved Queries' not in text
            assert 'top 10 results of 10' in text
            assert 'Device Discovery' not in text
            assert 'User Discovery' not in text
        self.wait_for_adapter_down(ui_consts.STRESSTEST_ADAPTER)
        self.wait_for_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def test_dashboard_data_with_trailing_space(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        with stress.contextmanager(take_ownership=True), stress_scanner.contextmanager(take_ownership=True):
            device_dict = {'device_count': 10, 'name': 'blah'}
            stress.add_client(device_dict)
            stress_scanner.add_client(device_dict)
            self.base_page.run_discovery()
            self.reports_page.create_report(ReportConfig(report_name=self.REPORT_NAME + ' ', add_dashboard=True))
            doc = self._extract_report_pdf_doc(self.REPORT_NAME)
            texts = [page.extractText() for page in doc.pages]
            text = ' '.join(texts)
            assert 'Device Discovery' in text
            assert 'User Discovery' in text
        self.wait_for_adapter_down(ui_consts.STRESSTEST_ADAPTER)
        self.wait_for_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def test_report_with_hebrew_name_and_text(self):
        smtp_service = MaildiranasaurusService()
        smtp_service.take_process_ownership()
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
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
            self.devices_page.customize_view_and_save(
                query_name=query_name,
                page_size=50,
                sort_field=self.devices_page.FIELD_HOSTNAME_TITLE,
                add_columns=[],
                remove_columns=[self.devices_page.FIELD_LAST_SEEN,
                                self.devices_page.FIELD_OS_TYPE,
                                self.devices_page.FIELD_ASSET_NAME,
                                self.devices_page.FIELD_HOSTNAME_TITLE],
                query_filter=self.devices_page.STRESSTEST_ADAPTER_FILTER

            )
            self.devices_page.click_row_checkbox()
            tag_name = 'טאג בעברית'
            self.devices_page.add_new_tags([tag_name])
            report_name = 'בדיקה'
            recipient = generate_random_valid_email()
            self.reports_page.create_report(
                ReportConfig(report_name=report_name,
                             add_dashboard=True,
                             queries=[{'entity': 'Devices', 'name': query_name}],
                             add_scheduling=True,
                             email_subject=report_name,
                             emails=[recipient]
                             )
            )
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
        self.wait_for_adapter_down(ui_consts.STRESSTEST_ADAPTER)
        self.wait_for_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def test_report_histogram_total(self):
        stress = stresstest_service.StresstestService()
        stress_scanner = stresstest_scanner_service.StresstestScannerService()
        with stress.contextmanager(take_ownership=True), stress_scanner.contextmanager(take_ownership=True):
            device_dict = {'device_count': 2000, 'name': 'blah'}
            stress.add_client(device_dict)
            stress_scanner.add_client(device_dict)

            self.base_page.run_discovery()

            report_name = 'report histogram test'
            self.reports_page.create_report(ReportConfig(report_name=report_name, add_dashboard=True))

            doc = self._extract_report_pdf_doc(report_name)

            assert doc.pages[0].extractText().count(report_name) == 1
            assert doc.pages[0].extractText().count('Generated on') == 1

            toc_page = doc.pages[1]

            assert toc_page.extractText().count('Discovery Summary') == 1
            assert toc_page.extractText().count('Dashboard Charts') == 1
            assert toc_page.extractText().count('Saved Queries') == 0

            self.dashboard_page.switch_to_page()
            dd_card = self.dashboard_page.find_device_discovery_card()
            quantities = self.dashboard_page.find_quantity_in_card_string(dd_card)

            discovery_charts_page = doc.pages[2]

            for quantity in quantities:
                assert str(quantity) in discovery_charts_page.extractText()

            dashboard_chart_page = doc.pages[3]

            assert dashboard_chart_page.extractText().count(MANAGED_DEVICES_QUERY_NAME) == 2

            new_query = 'histogram_query'

            self.devices_page.switch_to_page()
            self.devices_page.run_filter_and_save(new_query,
                                                  '(adapters == "stresstest_scanner_adapter")',
                                                  self.devices_page.FIELD_HOSTNAME_TITLE)

            histogram_title = 'histogram totals'
            self.dashboard_page.switch_to_page()
            self.dashboard_page.add_segmentation_card('Devices',
                                                      self.devices_page.FIELD_HOSTNAME_TITLE,
                                                      histogram_title,
                                                      view_name=new_query)

            self.reports_page.switch_to_page()
            self.reports_page.wait_for_table_to_load()
            self.reports_page.wait_for_spinner_to_end()
            self.reports_page.click_report(report_name)
            self.reports_page.wait_for_spinner_to_end()
            self.reports_page.click_save()

            doc = wait_until(self._extract_report_pdf_doc, check_return_value=False,
                             tolerated_exceptions_list=[StaleElementReferenceException],
                             report_name=report_name)

            self.dashboard_page.switch_to_page()
            card = self.dashboard_page.get_card(histogram_title)
            quantities = list(self.dashboard_page.get_histogram_items_quantities_on_pagination(card))[:6]
            total_items = self.dashboard_page.get_paginator_total_num_of_items(card)

            custom_charts_page = doc.pages[3]

            for quantity in quantities:
                assert str(quantity) in custom_charts_page.extractText()

            if int(total_items) > 6:
                assert f'Top 6 of {total_items}' in custom_charts_page.extractText()

        self.wait_for_adapter_down(ui_consts.STRESSTEST_ADAPTER)
        self.wait_for_adapter_down(ui_consts.STRESSTEST_SCANNER_ADAPTER)

    def _get_outline_titles(self, outlines):
        outline_titles = []
        for outline in outlines:
            if not isinstance(outline, list):
                outline_titles.append(str(outline.title))
            else:
                for inner_outline in self._get_outline_titles(outline):
                    outline_titles.append(inner_outline)
        return outline_titles
