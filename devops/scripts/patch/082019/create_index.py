import sys

import pymongo

from pymongo.collection import Collection
from axonius.entities import EntityType
from testing.services.plugins.aggregator_service import AggregatorService


def create_index_background(db: Collection, field: str):
    db.create_index([(field, pymongo.ASCENDING)], background=True)


# pylint: disable=protected-access
def main():
    ag = AggregatorService()
    print(f'Creating index in background..')
    create_index_background(ag._entity_db_map[EntityType.Devices], 'adapters.data.network_interfaces.ips_raw')
    create_index_background(ag._entity_db_map[EntityType.Devices], 'tags.data.network_interfaces.ips_raw')
    print(f'Done')


if __name__ == '__main__':
    sys.exit(main())
