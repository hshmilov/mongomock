from axonius.plugin_base import PluginBase

from axonius.utils.revving_cache import rev_cached_entity_type
from axonius.consts.plugin_consts import PLUGIN_NAME

from axonius.entities import EntityType


@rev_cached_entity_type(ttl=120)
def get_fielded_plugins(entity_type: EntityType):
    """
    Get all plugins that have fields, i.e. those that have returned at least one entity
    """
    # pylint: disable=W0212
    print('calculating fielded_plugins')
    return PluginBase.Instance._all_fields_db_map[entity_type].distinct(PLUGIN_NAME)
