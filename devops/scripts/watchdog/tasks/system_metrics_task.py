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
            self.report_process_stats()
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
                    self.report_metric(
                        f'{SystemMetric.HOST_DOCKER_STATS_KEY}.memory.current_ram_usage',
                        bytes_to_gb(memory_stats.get('usage') or 0),
                        container_name=container.name
                    )
                    self.report_metric(
                        f'{SystemMetric.HOST_DOCKER_STATS_KEY}.memory.max_ram_usage',
                        bytes_to_gb(memory_stats.get('max_usage') or 0),
                        container_name=container.name
                    )
                except Exception as e:
                    self.report_error(f'Failed getting stats for {container.name} - {e}')
        except Exception as e:
            self.report_error(f'failed to docker stats - {e}')

    def report_process_stats(self):
        try:
            processes = []
            for proc in psutil.process_iter():
                try:
                    # Get process name & pid from process object.
                    process_name = proc.name()
                    process_pid = proc.pid
                    memory_full_info = proc.memory_full_info()
                    env = proc.environ()
                    package = env.get('PACKAGE_NAME') or process_name or 'Unknown'
                    swap = round(memory_full_info.swap / (1024 ** 3), 2)
                    rss = round(memory_full_info.rss / (1024 ** 3), 2)
                    uss = round(memory_full_info.uss / (1024 ** 3), 2)
                    processes.append(
                        {
                            'process_pid': process_pid,
                            'process_name': process_name,
                            'process_package': package,
                            'process_swap': swap,
                            'process_uss': uss,
                            'process_rss': rss
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

            for sort_key in ['process_rss', 'process_swap']:
                try:
                    processes_by_rss = sorted(processes, key=lambda x: x.get(sort_key), reverse=True)
                    for i, proc in enumerate(processes_by_rss[:10]):
                        self.report_metric(
                            SystemMetric.PROCESSES + f'.sort_by_{sort_key}',
                            proc['process_package'] + '_' + str(proc.get(sort_key, '')),
                            order_in_sort=i,
                            **proc
                        )
                except Exception as e2:
                    self.report_error(f'failed to report process by rss - {e2}')
        except Exception as e:
            self.report_error(f'failed to report process stats - {e}')

    def report_collection_stats(self):
        try:
            ax = AxoniusService()
            all_collections = sorted(list(ax.db.client['aggregator'].list_collection_names()))

            for collection_name in all_collections:
                storage = get_collection_stats(ax.db.client['aggregator'][collection_name])

                self.report_metric(
                    SystemMetric.MONGO_AGGREGATOR_KEY + '.data',
                    bytes_to_gb(storage['storageSize']),
                    collection_name=collection_name
                )
                self.report_metric(
                    SystemMetric.MONGO_AGGREGATOR_KEY + '.indexes',
                    bytes_to_gb(storage['totalIndexSize']),
                    collection_name=collection_name
                )
                self.report_metric(
                    SystemMetric.MONGO_AGGREGATOR_KEY + '.total',
                    bytes_to_gb(storage['storageSize'] + storage['totalIndexSize']),
                    collection_name=collection_name
                )
                self.report_metric(
                    SystemMetric.MONGO_AGGREGATOR_KEY + '.in_memory',
                    bytes_to_gb(storage['size']),
                    collection_name=collection_name
                )

                wired_tiger = storage.get('wiredTiger') or {}
                available_for_reuse = (wired_tiger.get('block-manager') or {}).get('file bytes available for reuse')

                self.report_metric(
                    SystemMetric.MONGO_AGGREGATOR_KEY + '.available_for_reuse',
                    bytes_to_gb(available_for_reuse),
                    collection_name=collection_name
                )
        except Exception as e:
            self.report_error(f'Failed reporting collection stats - {e}')

    def report_unfinished_triggerables(self):
        try:
            ax = AxoniusService()
            for config in ax.db.client['core']['configs'].find(
                    {
                        'status': 'up'
                    }
            ):
                pun = config['plugin_unique_name']
                for triggerable in ax.db.client[pun]['triggerable_history'].find({
                    'job_completed_state': 'Running'
                }):
                    triggerable_started_at_utc = triggerable['started_at'].replace(tzinfo=None)
                    triggerable_already_running = datetime.datetime.utcnow() - triggerable_started_at_utc
                    self.report_metric(
                        f'{SystemMetric.TRIGGERABLE_RUNNING}.run_time',
                        triggerable_already_running,
                        plugin_unique_name=pun,
                        job_name=triggerable['job_name']
                    )
        except Exception as e:
            self.report_error(f'Failed reporting triggerables: {str(e)}')


if __name__ == '__main__':
    gw = SystemMetricsTask()
    gw.start()
