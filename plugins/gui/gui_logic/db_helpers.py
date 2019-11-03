from threading import Lock

import cachetools
from bson import ObjectId

from axonius.utils.get_plugin_base_instance import plugin_base_instance


@cachetools.cached(cachetools.TTLCache(maxsize=5000, ttl=24 * 3600), lock=Lock())
def translate_user_id_to_user_name(user_id: ObjectId):
    if user_id == '*':
        return 'Global'
    # pylint: disable=no-member
    # pylint: disable=protected-access
    user = plugin_base_instance()._users_collection.find_one({
        '_id': user_id
    })
    # pylint: disable=no-member
    # pylint: disable=protected-access
    if not user:
        return '[user has been deleted]'
    user_source = user['source']
    user_name = user['user_name']
    return f'{user_source}/{user_name}'


def beautify_db_entry(entry):
    """
    Renames the '_id' to 'date_fetched', and stores it as an id to 'uuid' in a dict from mongo
    :type entry: dict
    :param entry: dict from mongodb
    :return: dict
    """
    tmp = {
        **entry,
        'date_fetched': entry['_id'],
    }
    tmp['uuid'] = str(entry['_id'])
    del tmp['_id']
    user_id = tmp.get('user_id')
    if user_id is not None:
        tmp['associated_user_name'] = translate_user_id_to_user_name(user_id)
    return tmp
