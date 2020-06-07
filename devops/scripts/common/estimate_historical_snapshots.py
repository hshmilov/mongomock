import sys

from axonius.utils.mongo_administration import get_collection_stats
from services.axonius_service import AxoniusService


def main():
    ax = AxoniusService()

    all_collections = sorted(list(ax.db.client['aggregator'].list_collection_names()))

    for collection_name in all_collections:
        if not collection_name.startswith('historical_') or collection_name.endswith('_db_view'):
            continue
        storage_stats = get_collection_stats(ax.db.client['aggregator'][collection_name])
        storage = storage_stats['storageSize']
        indexes = storage_stats['totalIndexSize']
        total = storage + indexes
        print(
            f'Collection {collection_name}: '
            f'Storage {round(storage / (1024 ** 3), 2)} GB ',
            f'Indexes {round(indexes / (1024 ** 3), 2)} GB ',
            f'Total {round(total / (1024 ** 3), 2)} GB ',
        )


if __name__ == '__main__':
    sys.exit(main())
