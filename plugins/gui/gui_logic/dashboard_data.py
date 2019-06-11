import logging
from collections import defaultdict

from axonius.consts.plugin_consts import PLUGIN_NAME
from axonius.utils.revving_cache import rev_cached_entity_type
from axonius.plugin_base import PluginBase
from axonius.entities import EntityType

logger = logging.getLogger(f'axonius.{__name__}')


@rev_cached_entity_type(ttl=300)
def adapter_data(entity_type: EntityType):
    """
    See adapter_data
    """
    logger.info(f'Getting adapter data for entity {entity_type.name}')

    # pylint: disable=W0212
    entity_collection = PluginBase.Instance._entity_db_map[entity_type]
    adapter_entities = {
        'seen': 0, 'seen_gross': 0, 'unique': entity_collection.estimated_document_count(), 'counters': []
    }

    # First value is net adapters count, second is gross adapters count (refers to AX-2430)
    # If an Axonius entity has 2 adapter entities from the same plugin it will be counted for each time it is there
    entities_per_adapters = defaultdict(lambda: {'value': 0, 'meta': 0})
    for res in entity_collection.aggregate([{
            '$group': {
                '_id': f'$adapters.{PLUGIN_NAME}',
                'count': {
                    '$sum': 1
                }
            }
    }]):
        for plugin_name in set(res['_id']):
            entities_per_adapters[plugin_name]['value'] += res['count']
            adapter_entities['seen'] += res['count']

        for plugin_name in res['_id']:
            entities_per_adapters[plugin_name]['meta'] += res['count']
            adapter_entities['seen_gross'] += res['count']
    for name, value in entities_per_adapters.items():
        adapter_entities['counters'].append({'name': name, **value})

    return adapter_entities
