import re

import logging
from typing import Iterable

import pymongo

from axonius.modules.data.axonius_data import get_axonius_data_singleton
from axonius.entities import EntityType
from axonius.consts.gui_consts import (LAST_UPDATED_FIELD, PREDEFINED_FIELD)
from gui.logic.fielded_plugins import get_fielded_plugins
from gui.logic.filter_utils import filter_archived, filter_by_access_and_user

logger = logging.getLogger(f'axonius.{__name__}')


def _process_filter_views(entity_type: EntityType, mongo_filter):
    fielded_plugins = [re.match(r'([\w_]*?)(_\d+)?$', plugin_unique_name)[1] for plugin_unique_name in
                       get_fielded_plugins(entity_type)]
    logger.info('Filtering views that use fields from plugins without persisted fields schema')
    logger.info(f'Remaining plugins include: {fielded_plugins}')

    # If a query is predefined and has a reference to a plugin that doesn't exist - filter it out.
    # If a query is not predefined and private and wasn't created by the current logged user - filter it out.

    mongo_filter['query_type'] = mongo_filter.get('query_type', 'saved')
    return filter_archived({
        '$and': [
            mongo_filter,
            {
                '$or': [
                    {
                        '$and': [
                            {
                                PREDEFINED_FIELD: {
                                    '$ne': True
                                }
                            },
                            filter_by_access_and_user()
                        ]
                    },
                    {
                        '$and': [
                            {
                                PREDEFINED_FIELD: {
                                    '$eq': True
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
                    }
                ]
            }
        ]
    })


def get_views(entity_type: EntityType, limit, skip, mongo_filter, mongo_sort) -> Iterable[dict]:
    entity_views_collection = get_axonius_data_singleton().entity_views_collection[entity_type]

    if mongo_sort:
        sort = list(mongo_sort.items())
    else:
        sort = [(LAST_UPDATED_FIELD, pymongo.DESCENDING)]

    return entity_views_collection.find(_process_filter_views(entity_type, mongo_filter)). \
        sort(sort). \
        skip(skip). \
        limit(limit)


def get_views_count(entity_type: EntityType, mongo_filter, quick: bool = False):
    entity_views_collection = get_axonius_data_singleton().entity_views_collection[entity_type]
    processed_filter = _process_filter_views(entity_type, mongo_filter)
    if quick:
        return entity_views_collection.count_documents(processed_filter, limit=1000)
    return entity_views_collection.count_documents(processed_filter)
