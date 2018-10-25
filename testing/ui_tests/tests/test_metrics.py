import re

from axonius.utils.wait import wait_until
from services.adapters.stresstest_service import StresstestService
from services.adapters.stresstest_scanner_service import StresstestScannerService
from test_helpers.log_tester import LogTester
from ui_tests.tests.ui_consts import GUI_LOG_PATH
from ui_tests.tests.ui_test_base import TestBase


class TestMetrics(TestBase):
    def test_metrics(self):
        stress = StresstestService()
        stress_scanner = StresstestScannerService()
        with stress.contextmanager(take_ownership=True), stress_scanner.contextmanager(take_ownership=True):
            stress.add_client({'device_count': 10, 'name': 'blah'})
            stress_scanner.add_client({'device_count': 10, 'name': 'blah'})

            assert len(stress.clients()) == 1
            assert len(stress_scanner.clients()) == 1

            self.base_page.run_discovery()

            devices_unique = self.axonius_system.get_devices_db().count_documents({})
            users_unique = self.axonius_system.get_users_db().count_documents({})

            tester = LogTester(GUI_LOG_PATH)
            wait_until(lambda: tester.is_metric_in_log('system.gui.users', 2))
            wait_until(lambda: tester.is_metric_in_log('system.devices.seen', r'\d+'))  # TBD
            wait_until(lambda: tester.is_metric_in_log('system.devices.unique', devices_unique))
            wait_until(lambda: tester.is_metric_in_log('system.users.seen', r'\d+'))  # TBD
            wait_until(lambda: tester.is_metric_in_log('system.users.unique', users_unique))

            wait_until(lambda: tester.is_metric_in_log('adapter.devices.stresstest_adapter', 10))
            wait_until(lambda: tester.is_metric_in_log('adapter.devices.stresstest_scanner_adapter', 10))

            report = re.escape('adapters_data.active_directory_adapter.last_seen >= date("NOW - 7d")')
            wait_until(lambda: tester.is_metric_in_log('query.report', report))

            self.devices_page.switch_to_page()
            query_text = 'some_query_for_search'
            self.devices_page.fill_filter(query_text)
            self.devices_page.enter_search()

            wait_until(lambda: tester.is_metric_in_log('query.gui', query_text, lines_lookback=10))
