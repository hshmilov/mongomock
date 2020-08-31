import datetime
import time

import psutil
import docker
import netifaces

from axonius.consts.metric_consts import SystemMetric
from axonius.utils.mongo_administration import get_collection_stats
from scripts.watchdog.watchdog_task import WatchdogTask
from services.axonius_service import AxoniusService

SLEEP_SECONDS = 60 * 10


def bytes_to_gb(in_bytes):
    return round(in_bytes / (1024 ** 3), 2)


class SystemMetricsTask(WatchdogTask):
    def run(self):
        while True:
            self.report_interfaces()
            self.report_disk_space()
            self.report_memory()
            self.report_swap()
            self.report_docker_stats()
            self.report_collection_stats()
            self.report_unfinished_triggerables()
            time.sleep(SLEEP_SECONDS)

    def report_disk_space(self):

        try:
            client = docker.from_env()
            mongo_volume = client.volumes.get('mongo_data').attrs['Mountpoint']
            path = mongo_volume.split('docker')[0]
            usage = psutil.disk_usage(path)
            self.report_metric(SystemMetric.HOST_DB_DISK_FREE, bytes_to_gb(usage.free))
            self.report_metric(SystemMetric.HOST_DB_DISK_FREE_PERC, 100 - usage.percent)

            usage = psutil.disk_usage('/')
            self.report_metric(SystemMetric.HOST_ROOT_DISK_FREE, bytes_to_gb(usage.free))
            self.report_metric(SystemMetric.HOST_ROOT_DISK_FREE_PERC, 100 - usage.percent)

        except Exception as e:
            self.report_error(f'failed to fetch disk space data {e}')

    def report_interfaces(self):
        try:
            interfaces = netifaces.interfaces()
            self.report_metric(SystemMetric.NETIFACES_COUNT, len(interfaces))
        except Exception as e:
            self.report_error(f'failed to fetch interfaces data - {e}')

    def report_memory(self):
        try:
            virtual_memory = psutil.virtual_memory()
            self.report_metric(SystemMetric.HOST_VIRTUAL_MEMORY_TOTAL, bytes_to_gb(virtual_memory.total))
            self.report_metric(SystemMetric.HOST_VIRTUAL_MEMORY_AVAILABLE, bytes_to_gb(virtual_memory.available))
            self.report_metric(SystemMetric.HOST_VIRTUAL_MEMORY_PERCENT, virtual_memory.percent)
        except Exception as e:
            self.report_error(f'failed to report memory - {e}')

    def report_swap(self):
        try:
            swap = psutil.swap_memory()
            self.report_metric(SystemMetric.HOST_SWAP_TOTAL, bytes_to_gb(swap.total))
            self.report_metric(SystemMetric.HOST_SWAP_USED, bytes_to_gb(swap.used))
            self.report_metric(SystemMetric.HOST_SWAP_FREE, bytes_to_gb(swap.free))
            self.report_metric(SystemMetric.HOST_SWAP_PERCENT, swap.percent)
        except Exception as e:
            self.report_error(f'failed to swap memory - {e}')

    def report_docker_stats(self):
        try:
            client = docker.from_env()
            for container in client.containers.list():
                try:
                    if container.status != 'running':
                        continue

                    stats = container.stats(stream=False)
                    memory_stats = stats['memory_stats']
                    prefix = f'{SystemMetric.HOST_DOCKER_STATS_KEY}.{container.name}'
                    self.report_metric(f'{prefix}.memory.usage', bytes_to_gb(memory_stats.get('usage') or 0))
                    self.report_metric(f'{prefix}.memory.max_usage', bytes_to_gb(memory_stats.get('max_usage') or 0))
                except Exception as e:
                    self.report_error(f'Failed getting stats for {container.name} - {e}')
        except Exception as e:
            self.report_error(f'failed to docker stats - {e}')

    def report_collection_stats(self):
        try:
            ax = AxoniusService()
            all_collections = sorted(list(ax.db.client['aggregator'].list_collection_names()))

            for collection_name in all_collections:
                storage = get_collection_stats(ax.db.client['aggregator'][collection_name])

                metric_name = f'{SystemMetric.MONGO_AGGREGATOR_KEY}.{collection_name}'
                self.report_metric(metric_name + '.data', bytes_to_gb(storage['storageSize']))
                self.report_metric(metric_name + '.indexes', bytes_to_gb(storage['totalIndexSize']))
                self.report_metric(metric_name + '.total',
                                   bytes_to_gb(storage['storageSize'] + storage['totalIndexSize']))
                self.report_metric(metric_name + '.in_memory', bytes_to_gb(storage['size']))

                wired_tiger = storage.get('wiredTiger') or {}
                available_for_reuse = (wired_tiger.get('block-manager') or {}).get('file bytes available for reuse')
                self.report_metric(metric_name + '.available_for_reuse', bytes_to_gb(available_for_reuse))
        except Exception as e:
            self.report_error(f'Failed reporting collection stats - {e}')

    def report_unfinished_triggerables(self):
        try:
            ax = AxoniusService()
            for config in ax.db.client['core']['configs'].find(
                    {
                        'plugin_type': 'Adapter',
                        'status': 'up'
                    }
            ):
                pun = config['plugin_unique_name']
                for triggerable in ax.db.client[pun]['triggerable_history'].find({
                    'job_completed_state': 'Running'
                }):
                    triggerable_started_at_utc = triggerable['started_at'].replace(tzinfo=None)
                    triggerable_already_running = datetime.datetime.utcnow() - triggerable_started_at_utc
                    triggerable_key_prefix = f'{SystemMetric.TRIGGERABLE_RUNNING}.{pun}.{triggerable["job_name"]}'
                    self.report_metric(f'{triggerable_key_prefix}.start_time_utc', triggerable_started_at_utc)
                    self.report_metric(f'{triggerable_key_prefix}.run_time', triggerable_already_running)
        except Exception as e:
            self.report_error(f'Failed reporting triggerables: {str(e)}')


if __name__ == '__main__':
    gw = SystemMetricsTask()
    gw.start()
