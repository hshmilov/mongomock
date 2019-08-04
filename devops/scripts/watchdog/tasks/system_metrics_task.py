import time
import netifaces

from axonius.consts.metric_consts import SystemMetric
from scripts.watchdog.watchdog_task import WatchdogTask

SLEEP_SECONDS = 60 * 15


class SystemMetricsTask(WatchdogTask):
    def run(self):
        while True:
            interfaces = netifaces.interfaces()
            self.report_metric(SystemMetric.NETIFACES_COUNT, len(interfaces))
            time.sleep(SLEEP_SECONDS)


if __name__ == '__main__':
    gw = SystemMetricsTask()
    gw.start()
