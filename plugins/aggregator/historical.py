"""
This module handles logic with historical collection in aggregator service
"""
import datetime
import logging

from pymongo.database import Database as PyMongoDatabase
from pymongo.errors import PyMongoError

from aggregator.indices import common_db_indexes, non_historic_indexes
from axonius.entities import EntityType
from axonius.utils.host_utils import get_free_disk_space

logger = logging.getLogger(f'axonius.{__name__}')

# 30 GB
MIN_DISK_SIZE = ((1024 * 1024) * 1024) * 30


def create_retrospective_historic_collections(aggregator_db: PyMongoDatabase, historical_map):
    for entity_type in EntityType:
        col = historical_map[entity_type]
        for historical_date in sorted(col.distinct('accurate_for_datetime'), reverse=True):

            if get_free_disk_space() < MIN_DISK_SIZE:
                logger.warning(f'No more space left for historical collections')
                continue
            if (datetime.datetime.now() - historical_date).days > 30:
                continue
            new_col_name = f'historical_{entity_type.value.lower()}_{historical_date.strftime("%Y_%m_%d")}'
            if new_col_name in aggregator_db.list_collection_names():
                logger.info(f'Already inserted {new_col_name}')
                continue
            try:
                _create_historical_collection(new_col_name, entity_type, historical_date, aggregator_db, col)
            except Exception as e:
                logger.critical(f'failed creating historical and removing it {new_col_name}. Reason: {e}')


def _create_historical_collection(new_col_name, entity_type, historical_date, aggregator_db, history_col):
    try:
        new_col = aggregator_db.create_collection(new_col_name)
        logger.info(f'Created new collection {new_col_name}')
        history_col.aggregate([
            {'$match': {'accurate_for_datetime': historical_date}},
            {'$project': {'_id': 0}},
            {'$merge': new_col_name},
        ])
        logger.info(f'Finished transfer for collection {new_col_name}')
        # Indexes are created safely no need to catch exceptions
        common_db_indexes(new_col)
        non_historic_indexes(new_col)
        logger.info(f'Finished index for collection {new_col_name}')
    except PyMongoError:
        logger.critical(f'Failed to transfer data for {entity_type} on {new_col_name}')
        aggregator_db.drop_collection(new_col_name)
