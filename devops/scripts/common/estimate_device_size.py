import sys
import statistics
from collections import defaultdict

from axonius.entities import EntityType
from services.axonius_service import AxoniusService


def print_stats(entity_type, size_per_adapter: dict):
    print(f'---- Entity {str(entity_type)} -----')
    for adapter_name, data in size_per_adapter.items():
        print(f'Adapter {adapter_name} amount: {len(data)} storage: {round(sum(data) / 1024, 2)} MB')
        print(f'Average: {round(sum(data) / len(data), 2)} KB')
        print(f'Median: {round(statistics.median(data), 2)} KB')
        print(f'Max: {max(data)} KB')
        print(f'Min: {min(data)} KB')
        print(f' ')


def print_fields_stats(fields_stats: dict):
    for k in sorted(fields_stats, key=fields_stats.get, reverse=True):
        print(f'Field {k!r} size: {round(fields_stats[k] / (1024 ** 2), 2)} MB')

    print(f' ')


def main():
    ax = AxoniusService()

    try:
        count = int(sys.argv[1])
    except Exception:
        count = 1000

    try:
        entity = sys.argv[2]
        if entity.lower() == 'devices':
            all_entities = [EntityType.Devices]
        elif entity.lower() == 'users':
            all_entities = [EntityType.Users]
        else:
            print(f'No such entity {sys.argv[2]}, please write "devices" or "users"')
            return -1
    except Exception:
        all_entities = EntityType

    print(f'--------- NEW RUN -----------')
    print(f'Analyzing {count} entities...')

    for entity_type in all_entities:
        size_per_adapter = defaultdict(list)
        size_for_fields = defaultdict(int)
        db = ax.db.get_entity_db(entity_type)
        for i, device in enumerate(db.find({}).limit(count)):
            if i and i % 1000 == 0:
                print(f'Analyzed {i} entities of type {str(entity_type)} so far')

            if i and i % 100000 == 0:
                print_stats(entity_type, size_per_adapter)
                print_fields_stats(size_for_fields)

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

        print(f'Final stats')
        print_stats(entity_type, size_per_adapter)
        print_fields_stats(size_for_fields)


if __name__ == '__main__':
    sys.exit(main())
