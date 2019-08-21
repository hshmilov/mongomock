import time

import psutil
import netifaces
import docker

from axonius.consts.metric_consts import SystemMetric
from scripts.watchdog.watchdog_task import WatchdogTask

SLEEP_SECONDS = 60 * 30


class SystemMetricsTask(WatchdogTask):
    def run(self):
        while True:
            self.report_interfaces()
            self.report_disk_space()
            time.sleep(SLEEP_SECONDS)

    def report_disk_space(self):
        try:
            client = docker.from_env()
            mongo_volume = client.volumes.get('mongo_data').attrs['Mountpoint']
            path = mongo_volume.split('docker')[0]
            usage = psutil.disk_usage(path)
            self.report_metric(SystemMetric.HOST_DB_DISK_FREE_BYTES, usage.free)
            self.report_metric(SystemMetric.HOST_DB_DISK_FREE_PERC, 100 - usage.percent)

            usage = psutil.disk_usage('/')
            self.report_metric(SystemMetric.HOST_ROOT_DISK_FREE_BYTES, usage.free)
            self.report_metric(SystemMetric.HOST_ROOT_DISK_FREE_PERC, 100 - usage.percent)

        except Exception as e:
            self.report_error(f'failed to fetch disk space data {e}')

    def report_interfaces(self):
        try:
            interfaces = netifaces.interfaces()
            self.report_metric(SystemMetric.NETIFACES_COUNT, len(interfaces))
        except Exception as e:
            self.report_error(f'failed to fetch interfaces data - {e}')


if __name__ == '__main__':
    gw = SystemMetricsTask()
    gw.start()
