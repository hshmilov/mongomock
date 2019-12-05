import re

import logging
from typing import Iterable

import pymongo

from axonius.plugin_base import PluginBase
from axonius.entities import EntityType
from axonius.consts.gui_consts import (LAST_UPDATED_FIELD, PREDEFINED_FIELD)
from gui.gui_logic.fielded_plugins import get_fielded_plugins
from gui.gui_logic.filter_utils import filter_archived

logger = logging.getLogger(f'axonius.{__name__}')


def _process_filter_views(entity_type: EntityType, mongo_filter):
    fielded_plugins = [re.match(r'([\w_]*?)(_\d+)?$', plugin_unique_name)[1] for plugin_unique_name in
                       get_fielded_plugins(entity_type)]
    logger.info('Filtering views that use fields from plugins without persisted fields schema')
    logger.info(f'Remaining plugins include: {fielded_plugins}')

    # If a query is predefined and has a reference to a plugin that doesn't exist - filter it out.
    # If a query is not predefined, than we're fine
    mongo_filter['$or'] = [
        {
            PREDEFINED_FIELD: {
                '$ne': True
            }
        },
        {
            'view.query.filter': {
                '$not': {
                    '$regex': f'adapters_data.(?!{"|".join(fielded_plugins)}).'
                }
            }
        }
    ]
    mongo_filter['query_type'] = mongo_filter.get('query_type', 'saved')
    return filter_archived(mongo_filter)


def get_views(entity_type: EntityType, limit, skip, mongo_filter, mongo_sort) -> Iterable[dict]:
    entity_views_collection = PluginBase.Instance.gui_dbs.entity_query_views_db_map[entity_type]

    if mongo_sort:
        sort = list(mongo_sort.items())
    else:
        sort = [(LAST_UPDATED_FIELD, pymongo.DESCENDING)]

    return entity_views_collection.find(_process_filter_views(entity_type, mongo_filter)). \
        sort(sort). \
        skip(skip). \
        limit(limit)


def get_views_count(entity_type: EntityType, mongo_filter, quick: bool = False):
    entity_views_collection = PluginBase.Instance.gui_dbs.entity_query_views_db_map[entity_type]
    processed_filter = _process_filter_views(entity_type, mongo_filter)
    if quick:
        return entity_views_collection.count_documents(processed_filter, limit=1000)
    return entity_views_collection.count_documents(processed_filter)
