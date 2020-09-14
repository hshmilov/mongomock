"""
Like system metrics task, but for heavy things that should run less
"""
import statistics
import time
from collections import defaultdict

from axonius.consts.metric_consts import HeavySystemMetric
from axonius.entities import EntityType
from scripts.watchdog.watchdog_task import WatchdogTask
from services.axonius_service import AxoniusService

SLEEP_SECONDS = 60 * 60 * 12    # 12 hours


class HeavySystemMetricsTask(WatchdogTask):
    def run(self):
        while True:
            self.report_info(f'Starting a run of HeavySystemMetricsTask')
            self.report_entities_fields_stats()
            self.report_entities_raw_db_stats()
            time.sleep(SLEEP_SECONDS)

    def report_entities_fields_stats(self):
        self.report_info(f'Analyzing entities size in db')
        size_per_adapter = defaultdict(list)
        size_for_fields = defaultdict(int)
        try:
            ax = AxoniusService()

            for entity_type in EntityType:
                size_per_adapter = defaultdict(list)
                size_for_fields = defaultdict(int)
                db = ax.db.get_entity_db(entity_type)
                for i, device in enumerate(db.find({})):
                    if i and i % 100000 == 0:
                        self.report_info(f'Analyzed {i} entities of type {str(entity_type)} so far')

                    for adapter in device['adapters'] + device['tags']:
                        size_per_adapter[adapter['plugin_name']].append(len(str(adapter)) / 1024)

                        if isinstance(adapter.get('data'), dict):
                            for key, value in (adapter.get('data') or {}).items():
                                size_for_fields[key] += len(str(value))
                                if isinstance(value, list) and value:
                                    if isinstance(value[0], dict):
                                        for list_item in value:
                                            if isinstance(list_item, dict):
                                                for key_2, value_2 in list_item.items():
                                                    size_for_fields[f'{key}.{key_2}'] += len(str(value_2))
                                if isinstance(value, dict):
                                    for key_2, value_2 in value.items():
                                        size_for_fields[f'{key}.{key_2}'] += len(str(value_2))

                size_per_adapter = sorted(size_per_adapter.items(), key=lambda j: sum(j[1]), reverse=True)[:10]
                for i, k in enumerate(size_per_adapter):
                    k, data = k
                    self.report_metric(
                        HeavySystemMetric.ENTITIES_ADAPTERS_SIZE_KEY,
                        f'{i}_{str(entity_type)}_{k}_{round(sum(data) / 1024, 2)}mb',
                        entity_type=str(entity_type),
                        order_in_sort=i,
                        adapter_name=k,
                        size_of_dataset=len(data),
                        overall_size_for_adapter_mb=round(sum(data) / 1024, 2),
                        average_kb=round(sum(data) / len(data), 2),
                        median_kb=round(statistics.median(data), 2),
                        min_kb=min(data),
                        max_kb=max(data),
                    )

                for i, k in enumerate(sorted(size_for_fields, key=size_for_fields.get, reverse=True)[:10]):
                    size_for_field_in_mb = round(size_for_fields[k] / (1024 ** 2), 2)
                    self.report_metric(
                        HeavySystemMetric.ENTITIES_FIELDS_SIZE_KEY,
                        f'{i}_{str(entity_type)}_{k}_{size_for_field_in_mb}mb',
                        entity_type=str(entity_type),
                        field_name=k,
                        order_in_sort=i,
                        size_for_field_in_mb=size_for_field_in_mb
                    )
        except Exception as e:
            self.report_error(f'failed to report fields stats - {e}')
        finally:
            del size_per_adapter
            del size_for_fields

    def report_entities_raw_db_stats(self):
        self.report_info(f'Analyzing entities raw size in db')
        size_per_adapter = defaultdict(list)
        try:
            ax = AxoniusService()

            for entity_type in EntityType:
                size_per_adapter = defaultdict(list)
                db = ax.db.get_raw_entity_db(entity_type)
                for i, entity in enumerate(db.find({})):
                    if i and i % 500000 == 0:
                        self.report_info(f'Analyzed {i} raw entities of type {str(entity_type)} so far')

                    size_per_adapter[entity['plugin_unique_name']].append(len(str(entity)) / 1024)

                size_per_adapter = sorted(size_per_adapter.items(), key=lambda j: sum(j[1]), reverse=True)[:10]
                for i, k in enumerate(size_per_adapter):
                    k, data = k
                    self.report_metric(
                        HeavySystemMetric.ENTITIES_RAW_ADAPTERS_SIZE_KEY,
                        f'{i}_{str(entity_type)}_{k}_{round(sum(data) / 1024, 2)}mb',
                        entity_type=str(entity_type),
                        order_in_sort=i,
                        adapter_name=k,
                        size_of_dataset=len(data),
                        overall_size_for_adapter_mb=round(sum(data) / 1024, 2),
                        average_kb=round(sum(data) / len(data), 2),
                        median_kb=round(statistics.median(data), 2),
                        min_kb=min(data),
                        max_kb=max(data),
                    )
        except Exception as e:
            self.report_error(f'failed to report raw adapter stats - {e}')
        finally:
            del size_per_adapter


if __name__ == '__main__':
    gw = HeavySystemMetricsTask()
    gw.start()
