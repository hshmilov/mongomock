import sys
import statistics
from collections import defaultdict

from axonius.entities import EntityType
from services.axonius_service import AxoniusService


def main():
    ax = AxoniusService()

    try:
        count = int(sys.argv[1])
    except Exception:
        count = 1000

    print(f'Analyzing {count} entities...')

    for entity_type in EntityType:
        size_per_adapter = defaultdict(list)
        db = ax.db.get_entity_db(entity_type)
        for i, device in enumerate(db.find({}).limit(count)):
            if i and i % 1000 == 0:
                print(f'Analyzed {i} entities of type {str(entity_type)} so far')

            for adapter in device['adapters'] + device['tags']:
                size_per_adapter[adapter['plugin_name']].append(len(str(adapter)) / 1024)

        print(f'---- Entity {str(entity_type)} -----')
        for adapter_name, data in size_per_adapter.items():
            print(f'Adapter {adapter_name} amount: {len(data)} storage: {round(sum(data) / 1024, 2)} MB')
            print(f'Average: {round(sum(data) / len(data), 2)} KB')
            print(f'Median: {round(statistics.median(data), 2)} KB')
            print(f'Max: {max(data)} KB')
            print(f'Min: {min(data)} KB')
            print(f' ')


if __name__ == '__main__':
    sys.exit(main())
