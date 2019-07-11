import time
import requests
import urllib3

from axonius.consts.system_consts import NODE_MARKER_PATH
from scripts.watchdog.watchdog_task import WatchdogTask

SLEEP_SECONDS = 60 * 5
ERROR_MSG = 'UI is not responding'  # do not modify this string. used for alerts
NODE_MSG = 'this watchdog will not run on node'


class GuiAliveTask(WatchdogTask):
    def run(self):

        urllib3.disable_warnings()

        if NODE_MARKER_PATH.is_file():
            self.report_info(NODE_MSG)
            return

        while True:
            time.sleep(SLEEP_SECONDS)
            self.report_info(f'{self.name} is running')
            try:
                response = requests.get(f'https://localhost/api/signup', verify=False, timeout=(10, 30))
                if response.status_code != 200:
                    self.report_error(f'{ERROR_MSG} {response.status_code} {response.text}')
            except Exception as e:
                self.report_error(f'{ERROR_MSG} {e}')


if __name__ == '__main__':
    gw = GuiAliveTask()
    gw.start()
