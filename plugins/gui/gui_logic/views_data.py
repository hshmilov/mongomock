import re

import logging
import pymongo

from axonius.plugin_base import PluginBase

from axonius.entities import EntityType
from gui.gui_logic.fielded_plugins import get_fielded_plugins
from gui.gui_logic.filter_utils import filter_archived

logger = logging.getLogger(f'axonius.{__name__}')


def get_views(entity_type: EntityType, limit, skip, mongo_filter):
    entity_views_collection = PluginBase.Instance.gui_dbs.entity_query_views_db_map[entity_type]
    mongo_filter = filter_archived(mongo_filter)
    fielded_plugins = get_fielded_plugins(entity_type)

    def _validate_adapters_used(view):
        if not view.get('predefined'):
            return True
        for expression in view['view']['query'].get('expressions', []):
            adapter_matches = re.findall(r'adapters_data\.(\w*?)\.', expression.get('field', ''))
            if not adapter_matches:
                continue
            if list(filter(lambda x: all(x not in y for y in fielded_plugins), adapter_matches)):
                return False
        return True

    # Fetching views according to parameters given to the method
    all_views = entity_views_collection.find(mongo_filter).sort([('timestamp', pymongo.DESCENDING)]).skip(
        skip).limit(limit)
    logger.info('Filtering views that use fields from plugins without persisted fields schema')
    logger.info(f'Remaining plugins include: {fielded_plugins}')
    # Returning only the views that do not contain fields whose plugin has no field schema saved
    return list(filter(_validate_adapters_used, all_views))
