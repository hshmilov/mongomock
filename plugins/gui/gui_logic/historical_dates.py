from datetime import datetime
from typing import Dict

from axonius.entities import EntityType
from axonius.plugin_base import PluginBase
from axonius.utils.revving_cache import rev_cached


@rev_cached(ttl=600)
def first_historical_date() -> Dict[str, datetime]:
    """
    Returns the first available historical dates for all entities
    """
    dates = {}
    for entity_type in EntityType:
        # pylint: disable=W0212
        db = PluginBase.Instance._historical_entity_views_db_map[entity_type]
        historical_for_entity = db.find_one({},
                                            sort=[('accurate_for_datetime', 1)],
                                            projection=['accurate_for_datetime'])
        if historical_for_entity:
            dates[entity_type.value] = historical_for_entity['accurate_for_datetime']

    return dates


@rev_cached(ttl=600)
def all_historical_dates() -> Dict[str, datetime]:
    dates = {}
    for entity_type in EntityType:
        # pylint: disable=W0212
        db = PluginBase.Instance._historical_entity_views_db_map[entity_type]
        entity_dates = db.distinct('accurate_for_datetime')
        dates[entity_type.value] = {x.date().isoformat(): x.isoformat() for x in entity_dates}
    return dates
