import shutil

from axonius.utils.wait import wait_until
from devops.axonius_system import main as system_main
from scripts.watchdog.tasks.gui_alive_task import ERROR_MSG
from scripts.watchdog.watchdog_task import WATCHDOG_LOGS_DIR
from test_helpers.log_tester import LogTester


def test_gui_watchdog():
    shutil.rmtree(WATCHDOG_LOGS_DIR, ignore_errors=True)
    system_main('system up --restart'.split())
    system_main('service gui down'.split())

    log_tester = LogTester(WATCHDOG_LOGS_DIR / 'guialivetask.watchdog.log')
    wait_until(log_tester.is_str_in_log, str_in_log=ERROR_MSG, tolerated_exceptions_list=[Exception])
