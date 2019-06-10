import time
import requests

from axonius.consts.system_consts import NODE_MARKER_PATH
from scripts.watchdog.watchdog_task import WatchdogTask

SLEEP_SECONDS = 5
ERROR_MSG = 'UI is not responding'
NODE_MSG = 'this watchdog will not run on node'


class GuiAliveTask(WatchdogTask):
    def run(self):

        if NODE_MARKER_PATH.is_file():
            self.report_info(NODE_MSG)
            return

        while True:
            time.sleep(SLEEP_SECONDS)
            try:
                response = requests.get(f'https://localhost', verify=False, timeout=(10, 30))
                if response.status_code != 200:
                    self.report_error(f'{ERROR_MSG} {response.status_code} {response.text}')
            except Exception as e:
                self.report_error(f'{ERROR_MSG} {e}')


if __name__ == '__main__':
    gw = GuiAliveTask()
    gw.start()
