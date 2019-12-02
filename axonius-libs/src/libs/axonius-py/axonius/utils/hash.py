import hashlib

from axonius.entities import EntityType
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME


def get_preferred_internal_axon_id_from_dict(device_dict: dict, entity_type: EntityType) -> str:
    """
    See get_preferred_internal_axon_id
    Extracts the plugin_unique_name and id from the given device dict and uses the entity type given
    """
    return get_preferred_internal_axon_id(device_dict[PLUGIN_UNIQUE_NAME],
                                          device_dict['data']['id'], entity_type)


def get_preferred_internal_axon_id(plugin_unique_name: str, _id: str, entity_type: EntityType) -> str:
    """
    When saving entities, we want to try to maintain consistency as much as possible.
    https://axonius.atlassian.net/browse/AX-2980
    """
    return hashlib.md5(f'{entity_type.value}!{plugin_unique_name}!{_id}'.encode('utf-8')).hexdigest()


def get_preferred_quick_adapter_id(plugin_unique_name: str, _id: str) -> str:
    """
    Improved lookup performance
    https://axonius.atlassian.net/browse/AX-5214
    """
    # Warning! do not change. If you change, you affect aggregator_service.py which uses this function for migrations.
    # Change appropriately to include a v2 version.
    return f'{plugin_unique_name}!{_id}'
