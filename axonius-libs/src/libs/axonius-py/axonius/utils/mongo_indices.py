"""
This module holds index logic of aggregator service database

jim: 3.3: moved from plugins/aggregator/indices.py to here so that plugin_base can access
"""
import logging

import pymongo
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME, PLUGIN_NAME, ADAPTERS_LIST_LENGTH

logger = logging.getLogger(f'axonius.{__name__}')


def create_index_safe(collection, *args, **kwargs):
    """
    Creates an index on mongo, and only logs the exception instead of letting it propagate
    :param collection: collection to create index on
    :param args: args to pass to create_index function (see pymongo.collection.create_index)
    :param kwargs:  kwargs to pass to create_index function (see pymongo.collection.create_index)
    """
    try:
        logger.debug(f'Creating index {args}.')
        collection.create_index(*args, **kwargs)
    except PyMongoError as e:
        logger.critical(f'Exception while creating index {args}. reason: {e}')


def common_db_indexes(db: Collection):
    create_index_safe(db, [(f'adapters.{PLUGIN_NAME}', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'adapters.{PLUGIN_UNIQUE_NAME}', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(ADAPTERS_LIST_LENGTH, pymongo.DESCENDING)], background=True)
    create_index_safe(db, [('adapters.client_used', pymongo.DESCENDING)], background=True)

    # this is commonly filtered by the GUI
    create_index_safe(db, [('adapters.data.id', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [('adapters.pending_delete', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'adapters.data.adapter_properties', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'adapters.data.os.type', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'adapters.data.os.distribution', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'adapters.data.last_seen', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'adapters.data.hostname', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'adapters.data.name', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'adapters.data.network_interfaces.mac', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'adapters.data.network_interfaces.ips', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'adapters.data.network_interfaces.ips_raw', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'adapters.data.last_used_users', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'adapters.data.username', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'adapters.data.domain', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'adapters.data.installed_software.name', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'adapters.data.fetch_time', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'adapters.data.software_cves.cve_id', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'adapters.data.software_cves.cvss', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'adapters.data.installed_software.name', pymongo.ASCENDING)], background=True)

    create_index_safe(db, [('tags.data.id', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.{PLUGIN_NAME}', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.{PLUGIN_UNIQUE_NAME}', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.type', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.data.adapter_properties', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.data.os.type', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.data.os.distribution', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.data.last_seen', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.data.hostname', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.data.name', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.data.network_interfaces.mac', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.data.network_interfaces.ips', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.data.network_interfaces.ips_raw', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.data.last_used_users', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.data.username', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.data.domain', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.data.fetch_time', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.data.software_cves.cve_id', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.data.software_cves.cvss', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.data.installed_software.name', pymongo.ASCENDING)], background=True)

    # For labels
    create_index_safe(db, [(f'tags.name', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'tags.label_value', pymongo.ASCENDING)], background=True)

    # this is commonly sorted by
    create_index_safe(db, [('adapter_list_length', pymongo.DESCENDING)], background=True)


def non_historic_indexes(db: Collection):
    create_index_safe(db,
                      [(f'adapters.{PLUGIN_UNIQUE_NAME}', pymongo.ASCENDING),
                       ('adapters.data.id', pymongo.ASCENDING)
                       ], unique=True, background=True)
    create_index_safe(db,
                      [(f'adapters.data.last_seen', pymongo.ASCENDING), ('adapters.data.id', pymongo.ASCENDING)
                       ], background=True)
    create_index_safe(db, [('internal_axon_id', pymongo.ASCENDING)], unique=True, background=True)
    create_index_safe(db, [(f'adapters.quick_id', pymongo.ASCENDING)], background=True, unique=True)
    # Search index
    create_index_safe(db, [('adapters.data.hostname', pymongo.TEXT),
                           ('adapters.data.last_used_users', pymongo.TEXT),
                           ('adapters.data.username', pymongo.TEXT),
                           ('adapters.data.mail', pymongo.TEXT)],
                      background=True)


def historic_indexes(db: Collection):
    create_index_safe(db,
                      [(f'adapters.{PLUGIN_UNIQUE_NAME}', pymongo.ASCENDING),
                       ('adapters.data.id', pymongo.ASCENDING)
                       ], background=True)
    create_index_safe(db, [('internal_axon_id', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [(f'adapters.quick_id', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [('short_axon_id', pymongo.ASCENDING)], background=True)
    create_index_safe(db, [('accurate_for_datetime', pymongo.ASCENDING)], background=True)


def adapter_entity_raw_index(db: Collection):
    """
    Adds indices to the raw collection.
    A document in the raw collection looks as follows:
    {
        'plugin_unique_name': '',
        'id': '',
        'raw_data': {
            ...
        }
    }
    :param db: Collection to add indices too
    """
    create_index_safe(db,
                      [(f'{PLUGIN_UNIQUE_NAME}', pymongo.ASCENDING), ('id', pymongo.ASCENDING)
                       ], unique=True, background=True)


def adapter_entity_historical_raw_index(db: Collection):
    """
    Adds indices to the historical raw collection.
    A document in the raw collection looks as follows:
    {
        'plugin_unique_name': '',
        'id': '',
        'accurate_for_datetime': '',
        'raw_data': {
            ...
        }
    }
    :param db: Collection to add indices too
    """
    create_index_safe(db, [(f'{PLUGIN_UNIQUE_NAME}', pymongo.ASCENDING), ('id', pymongo.ASCENDING),
                           ('accurate_for_datetime', pymongo.ASCENDING)
                           ], unique=True, background=True)
