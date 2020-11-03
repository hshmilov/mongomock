import logging
from datetime import datetime

import dateutil
from bson import ObjectId
from dataclasses import dataclass
from dataclasses_json import DataClassJsonMixin


from axonius.utils.get_plugin_base_instance import plugin_base_instance
from axonius.utils.revving_cache import rev_cached
from axonius.consts.gui_consts import (UPDATED_BY_FIELD, PREDEFINED_PLACEHOLDER, IS_AXONIUS_ROLE, LAST_UPDATED_FIELD,
                                       PREDEFINED_FIELD)

logger = logging.getLogger(f'axonius.{__name__}')


def encode_datetime(obj):
    return obj.isoformat()


def decode_datetime(obj):
    return dateutil.parser.parse(obj)


@dataclass(frozen=True)
class UserInfo(DataClassJsonMixin):
    _id: str
    role_id: str = ''
    user_name: str = ''
    password: str = None
    source: str = ''
    first_name: str = ''
    last_name: str = ''
    last_updated: datetime = None
    pic_name: str = ''
    deleted: bool = False


@dataclass(frozen=True)
class Role(DataClassJsonMixin):
    name: str
    permissions: dict = None
    is_axonius_role: bool = False
    predefined: bool = False
    last_updated: datetime = None
    deleted: bool = False


@rev_cached(ttl=3600 * 24)
def translate_user_id_to_details(user_id: [str, ObjectId]) -> UserInfo:
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
    return get_user_info(user)


@rev_cached(ttl=3600 * 24)
def translate_user_to_details(user_name: str, source: str) -> UserInfo:
    """
    :param user_name: the user name from the db
    :param source: the user source Internal/External identity provider
    :return:        Simple class with the saved details of the requested user
    """

    # pylint: disable=no-member
    # pylint: disable=protected-access
    user = plugin_base_instance()._users_collection.find_one({
        'user_name': user_name,
        'source': source
    })
    return get_user_info(user)


def get_user_info(user):
    if not user or not user.get('user_name'):
        return None
    return UserInfo(str(user['_id']),
                    str(user['role_id']),
                    user['user_name'],
                    user['password'],
                    user.get('source', ''),
                    user.get('first_name', ''),
                    user.get('last_name', ''),
                    user.get(LAST_UPDATED_FIELD, None),
                    user.get('pic_name', ''),
                    user.get('archived', False))


@rev_cached(ttl=3600 * 24)
def translate_role_id_to_role(role_id: ObjectId) -> Role:
    """
    :param role_id: ObjectId to query from 'roles' collection
    :return:        Simple class with the role details
    """

    # pylint: disable=no-member
    # pylint: disable=protected-access
    role = plugin_base_instance()._roles_collection.find_one({
        '_id': role_id
    })
    if not role or not role.get('name'):
        return None

    return Role(role['name'],
                role['permissions'],
                role.get(IS_AXONIUS_ROLE, False),
                role.get(PREDEFINED_FIELD, False),
                role.get(LAST_UPDATED_FIELD))


def beautify_db_entry(entry, user_field_names=None):
    """
    Renames the '_id' to 'date_fetched', and stores it as an id to 'uuid' in a dict from mongo
    :type entry: dict
    :param entry: dict from mongodb
    :return: dict
    """
    tmp = {**entry, 'date_fetched': entry['_id']}
    tmp['uuid'] = str(entry['_id'])
    del tmp['_id']
    if not user_field_names:
        user_field_names = [UPDATED_BY_FIELD]
    for field in user_field_names:
        field_value = tmp.get(field)
        if field_value is not None:
            user_details = translate_user_id_to_details(field_value)
            if user_details:
                tmp[field] = user_details.to_json()
    return tmp


def clean_user_cache():
    translate_user_id_to_details.clean_cache()
    translate_user_to_details.clean_cache()
    translate_role_id_to_role.clean_cache()
