import re

import logging
import pymongo

from axonius.plugin_base import PluginBase

from axonius.entities import EntityType
from gui.gui_logic.fielded_plugins import get_fielded_plugins
from gui.gui_logic.filter_utils import filter_archived

logger = logging.getLogger(f'axonius.{__name__}')


def _process_filter_views(entity_type: EntityType, mongo_filter):
    fielded_plugins = [re.match(r'([\w_]*?)(_\d+)?$', plugin_unique_name)[1] for plugin_unique_name in
                       get_fielded_plugins(entity_type)]
    logger.info('Filtering views that use fields from plugins without persisted fields schema')
    logger.info(f'Remaining plugins include: {fielded_plugins}')
    mongo_filter['view.query.filter'] = {
        '$not': {
            '$regex': f'adapters_data.(?!{"|".join(fielded_plugins)}).'
        }
    }
    mongo_filter['query_type'] = mongo_filter.get('query_type', 'saved')
    return filter_archived(mongo_filter)


def get_views(entity_type: EntityType, limit, skip, mongo_filter):
    entity_views_collection = PluginBase.Instance.gui_dbs.entity_query_views_db_map[entity_type]
    return list(entity_views_collection.find(_process_filter_views(entity_type, mongo_filter)).sort(
        [('timestamp', pymongo.DESCENDING)]).skip(skip).limit(limit))


def get_views_count(entity_type: EntityType, mongo_filter, quick: bool = False):
    entity_views_collection = PluginBase.Instance.gui_dbs.entity_query_views_db_map[entity_type]
    processed_filter = _process_filter_views(entity_type, mongo_filter)
    if quick:
        return entity_views_collection.count_documents(processed_filter, limit=1000)
    return entity_views_collection.count_documents(processed_filter)
