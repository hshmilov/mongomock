import hashlib

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME


def get_preferred_internal_axon_id_from_dict(device_dict: dict) -> str:
    """
    See get_preferred_internal_axon_id
    Extracts the plugin_unique_name and id from the given device dict
    """
    return get_preferred_internal_axon_id(device_dict[PLUGIN_UNIQUE_NAME],
                                          device_dict['data']['id'])


def get_preferred_internal_axon_id(plugin_unique_name: str, _id: str) -> str:
    """
    When saving entities, we want to try to maintain consistency as much as possible.
    https://axonius.atlassian.net/browse/AX-2980
    """
    return hashlib.md5(f'{plugin_unique_name}!{_id}'.encode('utf-8')).hexdigest()
