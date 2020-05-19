import sys

from axonius.utils.mongo_administration import get_collection_storage_size
from services.axonius_service import AxoniusService


def main():
    ax = AxoniusService()

    all_collections = sorted(list(ax.db.client['aggregator'].list_collection_names()))

    for collection_name in all_collections:
        if not collection_name.startswith('historical_') or collection_name.endswith('_db_view'):
            continue
        storage = get_collection_storage_size(ax.db.client['aggregator'][collection_name])
        print(f'Collection {collection_name}: {round(storage / (1024 ** 3), 2)} GB')


if __name__ == '__main__':
    sys.exit(main())
