import shutil

from axonius.consts.metric_consts import SystemMetric
from axonius.utils.wait import wait_until
from devops.axonius_system import main as system_main
from scripts.watchdog.tasks.gui_alive_task import ERROR_MSG, SLEEP_SECONDS
from scripts.watchdog.watchdog_task import WATCHDOG_LOGS_DIR
from test_helpers.log_tester import LogTester


def test_watchdog_logs():
    shutil.rmtree(WATCHDOG_LOGS_DIR, ignore_errors=True)
    system_main('system up --restart'.split())
    system_main('service gui down'.split())

    gui_alive_tester = LogTester(WATCHDOG_LOGS_DIR / 'guialivetask.watchdog.log')
    wait_until(gui_alive_tester.is_str_in_log,
               str_in_log=ERROR_MSG,
               tolerated_exceptions_list=[Exception],
               total_timeout=SLEEP_SECONDS * 3)

    system_metric_tester = LogTester(WATCHDOG_LOGS_DIR / 'systemmetricstask.watchdog.log')
    wait_until(lambda: system_metric_tester.is_metric_in_log(SystemMetric.NETIFACES_COUNT, r'\d+'))
    wait_until(lambda: system_metric_tester.is_metric_in_log(SystemMetric.HOST_DB_DISK_FREE_PERC, r'\d+'))
    wait_until(lambda: system_metric_tester.is_metric_in_log(SystemMetric.HOST_DB_DISK_FREE, r'\d+'))
