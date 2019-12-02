from bson import ObjectId
from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin


from axonius.utils.get_plugin_base_instance import plugin_base_instance
from axonius.utils.revving_cache import rev_cached
from axonius.consts.gui_consts import (UPDATED_BY_FIELD, PREDEFINED_PLACEHOLDER)


@dataclass(frozen=True)
class UserInfo(DataClassJsonMixin):
    username: str
    source: str = ''
    first_name: str = ''
    last_name: str = ''
    deleted: bool = False


@rev_cached(ttl=3600 * 24)
def translate_user_id_to_details(user_id: ObjectId) -> UserInfo:
    """
    :param user_id: ObjectId to query from 'users' collection
    :return:        Simple class with the saved details of the requested user
    """
    if user_id == '*':
        return UserInfo(PREDEFINED_PLACEHOLDER)
    # pylint: disable=no-member
    # pylint: disable=protected-access
    user = plugin_base_instance()._users_collection.find_one({
        '_id': user_id
    })
    if not user or not user.get('user_name'):
        return None

    return UserInfo(user['user_name'],
                    user.get('source', ''),
                    user.get('first_name', ''),
                    user.get('last_name', ''),
                    user.get('archived', False))


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
    updated_by_id = tmp.get(UPDATED_BY_FIELD)
    if updated_by_id is not None:
        tmp[UPDATED_BY_FIELD] = translate_user_id_to_details(updated_by_id).to_json()
    return tmp
