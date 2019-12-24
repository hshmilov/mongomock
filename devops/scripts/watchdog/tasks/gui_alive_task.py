import time
import requests
import urllib3
from pathlib import Path

from axonius.consts.system_consts import NODE_MARKER_PATH
from scripts.watchdog.watchdog_task import WatchdogTask

SLEEP_SECONDS = 60 * 1
ERROR_MSG = 'UI is not responding'  # do not modify this string. used for alerts
NODE_MSG = 'this watchdog will not run on node'
LOCKFILE = Path('/tmp/upgrade.lock')
INTERNAL_PORT = 4433    # 0.0.0.0:443 could be mutual-tls protected. The host exposes 127.0.0.1:4433 without it.


class GuiAliveTask(WatchdogTask):
    def run(self):

        urllib3.disable_warnings()

        while True:
            if NODE_MARKER_PATH.is_file():
                self.report_info(NODE_MSG)
                return

            time.sleep(SLEEP_SECONDS)

            if LOCKFILE.is_file():
                self.report_info('upgrade is in progress...')
                continue

            self.report_info(f'{self.name} is running')
            try:
                response = requests.get(f'https://localhost:{INTERNAL_PORT}/api/signup', verify=False, timeout=(10, 20))
                if response.status_code != 200:
                    self.report_error(f'{ERROR_MSG} {response.status_code} {response.text}')
            except Exception as e:
                self.report_error(f'{ERROR_MSG} {e}')


if __name__ == '__main__':
    gw = GuiAliveTask()
    gw.start()
