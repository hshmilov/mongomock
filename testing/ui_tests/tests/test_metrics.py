import re

from axonius.utils.wait import wait_until
from axonius.consts.metric_consts import SystemMetric, Query
from services.adapters.stresstest_service import StresstestService
from services.adapters.stresstest_scanner_service import StresstestScannerService
from test_helpers.log_tester import LogTester
from ui_tests.tests.ui_consts import GUI_LOG_PATH
from ui_tests.tests.ui_test_base import TestBase


class TestMetrics(TestBase):
    TEST_METRIC_QUERY_NAME = 'test_metric_query_1'

    def test_metrics(self):
        stress = StresstestService()
        stress_scanner = StresstestScannerService()
        with stress.contextmanager(take_ownership=True), stress_scanner.contextmanager(take_ownership=True):
            stress.add_client({'device_count': 10, 'name': 'blah'})
            stress_scanner.add_client({'device_count': 10, 'name': 'blah'})

            assert len(stress.clients()) == 1
            assert len(stress_scanner.clients()) == 1

            metric_query = 'specific_data.data.os.major == 1'
            self.devices_page.switch_to_page()
            self.devices_page.fill_filter(metric_query)
            self.devices_page.enter_search()
            self.devices_page.click_save_query()
            self.devices_page.fill_query_name(self.TEST_METRIC_QUERY_NAME)
            self.devices_page.click_save_query_save_button()

            self.base_page.run_discovery()

            devices_unique = self.axonius_system.get_devices_db().count_documents({})
            users_unique = self.axonius_system.get_users_db().count_documents({})

            tester = LogTester(GUI_LOG_PATH)
            # do not modify anything relate to metrics!
            wait_until(lambda: tester.is_metric_in_log(SystemMetric.GUI_USERS, 2))
            wait_until(lambda: tester.is_metric_in_log(SystemMetric.DEVICES_SEEN, r'\d+'))  # TBD
            wait_until(lambda: tester.is_metric_in_log(SystemMetric.DEVICES_UNIQUE, devices_unique))
            wait_until(lambda: tester.is_metric_in_log(SystemMetric.USERS_SEEN, r'\d+'))  # TBD
            wait_until(lambda: tester.is_metric_in_log(SystemMetric.USERS_UNIQUE, users_unique))

            wait_until(lambda: tester.is_metric_in_log('adapter.devices.stresstest_adapter.entities', 10))
            wait_until(lambda: tester.is_metric_in_log('adapter.devices.stresstest_adapter.entities.meta', 10))
            wait_until(lambda: tester.is_metric_in_log('adapter.devices.stresstest_scanner_adapter.entities', 10))
            wait_until(lambda: tester.is_metric_in_log('adapter.devices.stresstest_scanner_adapter.entities.meta', 10))

            wait_until(lambda: tester.is_metric_in_log('adapter.users.json_file_adapter.entities', 2))
            wait_until(lambda: tester.is_metric_in_log('adapter.users.json_file_adapter.entities.meta', 2))
            wait_until(lambda: tester.is_metric_in_log('adapter.users.active_directory_adapter.entities', r'\d+'))
            wait_until(lambda: tester.is_metric_in_log('adapter.users.active_directory_adapter.entities.meta', r'\d+'))

            system_scheduler_log_tester = self.axonius_system.scheduler.log_tester
            wait_until(lambda: system_scheduler_log_tester.is_metric_in_log(SystemMetric.TRIAL_EXPIRED_STATE, False))
            wait_until(lambda: system_scheduler_log_tester.is_metric_in_log(SystemMetric.CYCLE_FINISHED, r'\d+'))

            report = re.escape(metric_query)

            self._create_report(metric_query)

            wait_until(lambda: tester.is_metric_in_log('query.report', report))

            self.devices_page.switch_to_page()
            query_text = 'some_query_for_search'
            self.devices_page.fill_filter(query_text)
            self.devices_page.enter_search()

            wait_until(lambda: tester.is_metric_in_log(Query.QUERY_GUI, query_text))

    def _create_report(self, metric_query):
        self.reports_page.switch_to_page()
        self.reports_page.wait_for_table_to_load()
        self.reports_page.click_new_report()
        self.reports_page.click_add_scheduling()
        self.reports_page.find_missing_email_server_notification()
        self.reports_page.fill_report_name(metric_query)
        self.reports_page.click_include_dashboard()
        self.reports_page.click_include_queries()
        self.reports_page.select_saved_view(self.TEST_METRIC_QUERY_NAME)
        self.reports_page.click_save()
