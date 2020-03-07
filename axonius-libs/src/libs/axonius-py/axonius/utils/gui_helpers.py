# pylint: disable=too-many-lines
import io
import json
import logging
import itertools
import os
import re
from collections import defaultdict
from datetime import datetime
from enum import Enum
from threading import Lock
from typing import NamedTuple, Iterable, List, Union, Dict

import cachetools
import dateutil
import pymongo

from bson import ObjectId
from flask import request, session, g

from axonius.consts.gui_consts import SPECIFIC_DATA, ADAPTERS_DATA, JSONIFY_DEFAULT_TIME_FORMAT, MAX_SORTED_FIELDS, \
    MIN_SORTED_FIELDS, PREFERRED_FIELDS, MAX_DAYS_SINCE_LAST_SEEN, SPECIFIC_DATA_PREFIX_LENGTH, \
    ADAPTER_CONNECTIONS_FIELD, DISTINCT_ADAPTERS_COUNT_FIELD

from axonius.entities import EntitiesNamespace

from axonius.consts.plugin_consts import (ADAPTERS_LIST_LENGTH, PLUGIN_NAME,
                                          PLUGIN_UNIQUE_NAME, GUI_PLUGIN_NAME)
from axonius.devices.device_adapter import DeviceAdapter
from axonius.plugin_base import EntityType, add_rule, return_error, PluginBase
from axonius.users.user_adapter import UserAdapter
from axonius.utils.axonius_query_language import parse_filter, parse_filter_non_entities, PREFERRED_SUFFIX
from axonius.utils.revving_cache import rev_cached_entity_type
from axonius.utils.threading import singlethreaded
from axonius.utils.dict_utils import is_filter_in_value
from axonius.utils import serial_csv

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=C0302
# too many lines in this module!

# the maximal amount of data a pagination query will give
PAGINATION_LIMIT_MAX = 2000

FIELDS_TO_PROJECT = ['internal_axon_id', 'adapters.pending_delete', f'adapters.{PLUGIN_NAME}',
                     'tags.type', 'tags.name', f'tags.{PLUGIN_NAME}',
                     'accurate_for_datetime', ADAPTERS_LIST_LENGTH,
                     'tags.data', 'adapters.client_used']

FIELDS_TO_PROJECT_FOR_GUI = ['internal_axon_id', 'adapters', 'unique_adapter_names', 'labels', ADAPTERS_LIST_LENGTH]

SUBSTRING_FIELDS = ['hostname']


def check_permissions(user_permissions, required_permissions, request_action: str) -> bool:
    """
    Checks whether user_permissions has all required_permissions
    :param request_action: POST, GET, ...
    :return: whether or not it has all permissions
    """
    if required_permissions:
        for required_perm in required_permissions:
            curr_level = user_permissions.get(required_perm.Type, PermissionLevel.Restricted)
            required_perm_level = required_perm.Level
            if curr_level == PermissionLevel.ReadWrite:
                continue
            elif curr_level == PermissionLevel.ReadOnly:
                if required_perm_level == ReadOnlyJustForGet:
                    if request_action != 'GET':
                        return False
                    continue
                elif required_perm_level == PermissionLevel.ReadOnly:
                    continue
                elif required_perm_level == PermissionLevel.ReadWrite:
                    return False

            else:
                # implied that curr_level == PermissionLevel.Restricted
                return False
    return True


def deserialize_db_permissions(permissions):
    """
    Converts DB-like permissions to pythonic types
    """
    return {
        PermissionType[k]: PermissionLevel[v] for k, v in permissions.items()
    }


def is_admin_user():
    return session.get('user', {}).get('admin', False)


def get_user_permissions():
    return session.get('user', {}).get('permissions', {})


# This is sort of an extension for the enum below, this can be used instead of PermissionLevel.* for
# marking required permissions for endpoints and it means that ReadOnly is required for GET requests
# while any other type (DELETE, PUT, POST) require ReadWrite permissions
# pylint: disable=invalid-name
ReadOnlyJustForGet = object()
# pylint: enable=invalid-name


# Represent the level of access granted to a user
class PermissionLevel(Enum):
    Restricted = 'Restricted'
    ReadOnly = 'Read only'
    ReadWrite = 'Read and edit'


# Represent the possible aspects of the system the user might access
class PermissionType(Enum):
    Settings = 'Settings'
    Adapters = 'Adapters'
    Devices = 'Devices'
    Users = 'Users'
    Enforcements = 'Enforcements'
    Dashboard = 'Dashboard'
    Reports = 'Reports'
    Instances = 'Instances'


# Represent a permission in the system
class Permission(NamedTuple):
    Type: PermissionType
    Level: PermissionLevel


# Caution! These decorators must come BEFORE @add_rule
def add_rule_custom_authentication(rule, auth_method, *args, **kwargs):
    """
    A URL mapping for methods that are exposed to external services, i.e. browser or applications
    :param rule: rule name
    :param auth_method: An auth method
    """
    # the should_authenticate=False means that we're not checking API-Key,
    # because those are APIs exposed to either the browser or external applications
    add_rule_res = add_rule(rule, should_authenticate=False, *args, **kwargs)
    if auth_method is not None:
        return lambda func: auth_method(add_rule_res(func))
    return add_rule_res


def add_rule_unauth(rule, *args, **kwargs):
    """
    A URL mapping for GUI/API endpoints that work even if the user is not logged in, e.g. the login mechanism itself
    """
    return add_rule_custom_authentication(rule, None, *args, **kwargs)


# Caution! These decorators must come BEFORE @add_rule
def filtered():
    """
        Decorator stating that the view supports ?filter=... - to be used when the filter isn't expected to run on
        entities
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            filter_expr = None
            try:
                filter_expr = request.args.get('filter', '')
                history_date = request.args.get('history')
                filter_obj = parse_filter_non_entities(filter_expr, history_date)
            except Exception as e:
                logger.warning(f'Failed in mongo filter {func} with \'{filter_expr}\'', exc_info=True)
                return return_error('Could not create mongo filter. Details: {0}'.format(e), 400)
            return func(self, mongo_filter=filter_obj, *args, **kwargs)

        return actual_wrapper

    return wrap


def filtered_entities():
    """
        Decorator stating that the view supports ?filter=... when the filter is expected to run on entities
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            filter_expr = None
            try:
                content = self.get_request_data_as_object() if request.method == 'POST' else request.args
                filter_expr = content.get('filter')
                history_date = content.get('history')
                filter_obj = parse_filter(filter_expr, history_date)
            except Exception as e:
                logger.warning(f'Failed in mongo filter on {func} on \'{filter_expr}\'', exc_info=True)
                return return_error('Could not create mongo filter. Details: {0}'.format(e), 400)
            return func(self, mongo_filter=filter_obj, *args, **kwargs)

        return actual_wrapper

    return wrap


def sorted_endpoint():
    """
    Decorator stating that the view supports ?sort=<field name><'-'/'+'>
    The field name must match a field in the collection to sort by
    and the -/+ determines whether sort is descending or ascending
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            sort_obj = {}
            try:
                content = self.get_request_data_as_object() if request.method == 'POST' else request.args
                sort_param = content.get('sort')
                desc_param = content.get('desc')
                if sort_param:
                    logger.info(f'Parsing sort: {sort_param}')
                    direction = pymongo.DESCENDING if desc_param == '1' else pymongo.ASCENDING

                    if sort_param == 'labels':
                        sort_obj['tags.label_value'] = direction
                    else:
                        splitted = sort_param.split('.')
                        if splitted[0] == SPECIFIC_DATA or splitted[0] == ADAPTERS_DATA:
                            if splitted[0] == ADAPTERS_DATA:
                                splitted[1] = 'data'

                            splitted[0] = 'adapters'
                            sort_obj['.'.join(splitted)] = direction
                        else:
                            sort_obj[sort_param] = direction
            except Exception as e:
                return return_error('Could not create mongo sort. Details: {0}'.format(e), 400)
            return func(self, mongo_sort=sort_obj, *args, **kwargs)

        return actual_wrapper

    return wrap


# Caution! These decorators must come BEFORE @add_rule
def projected():
    """
    Decorator stating that the view supports ?fields=['name','hostname',['os_type':'OS.type']]
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            mongo_projection = None
            content = self.get_request_data_as_object() if request.method == 'POST' else request.args
            field_names = content.get('fields')
            if field_names:
                try:
                    mongo_projection = {}
                    for field_part in field_names.split(','):
                        mongo_projection[field_part] = 1
                except json.JSONDecodeError:
                    logger.exception(f'Failed to decode mongo projection {mongo_projection}')
            return func(self, mongo_projection=mongo_projection, *args, **kwargs)

        return actual_wrapper

    return wrap


def schema_fields():
    """
    Relevant only if the request.method is POST
    Decorator stating that the schema array of schema_fields=[{'name': <field name>, 'title': <field title>},...]
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            fields = []
            if request.method == 'POST':
                content = self.get_request_data_as_object()
                fields = content.get('schema_fields')
            return func(self, schema_fields=fields, *args, **kwargs)
        return actual_wrapper

    return wrap


def filtered_fields():
    """
    Assumes the request.method is POST
    The property 'field_filters', sent in the request data, is added as an argument to the decorated method
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            field_filters = self.get_request_data_as_object().get('field_filters', {})
            return func(self, field_filters=field_filters, *args, **kwargs)

        return actual_wrapper

    return wrap


def accounts():
    """
    Relevant only if the request.method is POST
    Decorator stating that the accounts array=['account_1', 'account_2'...]
    """
    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            accounts_list = []
            if request.method == 'POST':
                content = self.get_request_data_as_object()
                accounts_list = content.get('accounts')
            return func(self, accounts=accounts_list, *args, **kwargs)
        return actual_wrapper
    return wrap


def paginated(limit_max=PAGINATION_LIMIT_MAX):
    """
    Decorator stating that the view supports '?limit=X&start=Y' for pagination
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            # it's fine to raise here - an exception will be nicely JSONly displayed by add_rule
            content = self.get_request_data_as_object() if request.method == 'POST' else request.args
            try:
                limit = int(content.get('limit'))
            except TypeError:
                limit = limit_max
            if limit < 0:
                raise ValueError('Limit must not be negative')
            if limit > limit_max:
                logger.warning(f'GUI asked for too many records: {limit}')
                limit = limit_max
            try:
                skip = int(content.get('skip'))
            except TypeError:
                skip = 0
            if skip < 0:
                raise ValueError('start must not be negative')
            return func(self, limit=limit, skip=skip, *args, **kwargs)

        return actual_wrapper

    return wrap


def search_filter():
    """
    Decorator stating that the view supports '?search=X' for filtering chart data by name
    """
    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            # it's fine to raise here - an exception will be nicely JSONly displayed by add_rule
            content = request.args if request.method == 'GET' else self.get_request_data_as_object()
            term = content.get('search', '')
            return func(self, search=term, *args, **kwargs)

        return actual_wrapper

    return wrap


def historical_range(force: bool = False):
    """
    Decorator stating that the view supports '?date_from=DATE&date_to=DATE' for historical views
    :param force: If True, then empty date will not be accepted
    """

    def wrap(func):
        def raise_or_return(err):
            if force:
                raise ValueError(err)

        def try_get_date():
            from_given_date = request.args.get('date_from')
            if not from_given_date:
                return raise_or_return('date_from must be provided')
            to_given_date = request.args.get('date_to')
            if not to_given_date:
                return raise_or_return('date_to must be provided')
            try:
                from_given_date = dateutil.parser.parse(from_given_date)
                to_given_date = dateutil.parser.parse(to_given_date)
            except Exception:
                raise ValueError('Dates are invalid')
            return from_given_date, to_given_date

        def actual_wrapper(self, *args, **kwargs):
            got_date = try_get_date()
            from_date, to_date = None, None
            if got_date:
                from_date, to_date = got_date
            return func(self, from_date=from_date, to_date=to_date, *args, **kwargs)

        return actual_wrapper

    return wrap


def historical():
    """
    Decorator stating that the view supports '?history=EXACT_DATE' for historical views
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            content = self.get_request_data_as_object() if request.method == 'POST' else request.args
            history = content.get('history')
            if history:
                try:
                    history = dateutil.parser.parse(history)
                except Exception:
                    return return_error('Specified date is invalid')
                logger.info(f'historical for {history}')
            return func(self, history=history, *args, **kwargs)

        return actual_wrapper

    return wrap


# This is here to support HOT=true for testing
if os.environ.get('HOT') == 'true':
    def get_connected_user_id() -> ObjectId:
        """
        Returns the current connected user's id
        """
        # pylint: disable=no-member
        # pylint: disable=protected-access
        return PluginBase.Instance._users_collection.find_one({'user_name': 'admin'})['_id']
        # pylint: enable=no-member
        # pylint: disable=protected-access
else:
    def get_connected_user_id() -> ObjectId:
        """
        Returns the current connected user's id
        """
        if 'api_request_user' in g:
            return g.api_request_user['_id']
        return session['user']['_id']


def get_historized_filter(entities_filter, history_date: datetime):
    """
    If you wish to write generic code for both historical data and non historical data
    You can build the appropriate mongo filter using this method by passing the desired filter
    and the date to fetch for
    :param entities_filter: the desired mongo filter
    :param history_date: the desired date to fetch for, or None for latest
    :return: processed filter
    """
    if history_date:
        entities_filter = {
            '$and': [
                entities_filter,
                {
                    'accurate_for_datetime': history_date
                }
            ]
        }
    return entities_filter


def is_adapter_count_query(query):
    if '$where' in query:
        return True
    if isinstance(query, str):
        return False
    for k, v in query.items():
        # pylint: disable=no-else-return
        if isinstance(v, dict):
            return is_adapter_count_query(v)
        elif isinstance(v, list):
            for list_item in v:
                return is_adapter_count_query(list_item)
    return False
# pylint: disable=no-else-return


def get_entities_count(entities_filter, entity_collection, history_date: datetime = None, quick: bool = False):
    """
    Count total number of devices answering given mongo_filter.
    If 'quick' is True, then will only count until 1000.
    """
    processed_filter = get_historized_filter(entities_filter, history_date)
    is_adapter_count = is_adapter_count_query(processed_filter)
    if quick and is_adapter_count:
        return entity_collection.count(processed_filter, limit=1000)
    elif quick and not is_adapter_count:
        return entity_collection.count_documents(processed_filter, limit=1000)

    if not processed_filter:
        return entity_collection.estimated_document_count()
    elif is_adapter_count:
        return entity_collection.count(processed_filter)
    return entity_collection.count_documents(processed_filter)


# pylint: disable=too-many-return-statements,too-many-branches,too-many-statements
def find_entity_field(entity_data, field_path, skip_unique=False, specific_adapter=None):
    """
    Recursively expand given entity, following period separated properties of given field_path,
    until reaching the requested value

    :param entity_data: A nested dict representing parsed values of an entity
    :param field_path:  A path to a field ('.' separated chain of keys)
    :return:
    """
    def return_field_max():
        result = find_entity_field(entity_data, field_path, skip_unique=True)
        if result is None:
            result = []
        if not isinstance(result, list):
            result = [result]
        if result:
            try:
                return max(result)
            except Exception:
                return result[0]
        return None

    def return_field_min():
        result = find_entity_field(entity_data, field_path, skip_unique=True)
        if result is None:
            result = []
        if not isinstance(result, list):
            result = [result]
        if result:
            try:
                return min(result)
            except Exception:
                return result[0]
        return None

    def return_true_if_list():
        result = find_entity_field(entity_data, field_path, skip_unique=True)
        if isinstance(result, list) and True in result and False in result:
            return True
        return result

    if not skip_unique:
        if field_path in MAX_SORTED_FIELDS:
            return return_field_max()
        if field_path in MIN_SORTED_FIELDS:
            return return_field_min()
        if field_path in ['specific_data.data.part_of_domain',
                          'specific_data.data.device_disabled',
                          'specific_data.data.os.is_windows_server']:
            return return_true_if_list()

    if entity_data is None:
        # Return no value for this path
        return ''

    if specific_adapter is not None and specific_adapter in entity_data['adapters_data']:
        try:
            # As far as i checked every adapter return only 1 value thats why the hard-code 0 index...
            return entity_data['adapters_data'][specific_adapter][0][field_path], \
                entity_data['adapters_data'][specific_adapter][0]['last_seen']
        except Exception:
            return None, None
    elif specific_adapter is not None:
        return None, None

    if not field_path or isinstance(entity_data, str):
        # Return value corresponding with given path
        return entity_data

    if not isinstance(entity_data, list):
        first_dot = field_path.find('.')
        if first_dot == -1:
            # Return value of last key in the chain
            return entity_data.get(field_path)
        # Continue recursively with value of current key and rest of path
        return find_entity_field(entity_data.get(field_path[:first_dot]), field_path[first_dot + 1:])

    if len(entity_data) == 1:
        # Continue recursively on the single element in the list, with the same path
        return find_entity_field(entity_data[0], field_path)

    children = []
    for item in entity_data:
        # Continue recursively for current element of the list
        child_value = find_entity_field(item, field_path)
        if child_value is not None and child_value != '' and child_value != []:
            def new_instance(value):
                """
                Test if given value is not yet found in the children list, according to comparison rules.
                For strings, if value is a prefix of or has a prefix in the list, is considered to be found.
                :param value:   Value for testing if exists in the list
                :return: True, if value is new to the children list and False otherwise
                """

                def same_string(x, y):
                    if not isinstance(x, str):
                        return False
                    if not isinstance(y, str):
                        return False
                    x = x.lower().strip()
                    y = y.lower().strip()

                    last_part = field_path.split('.')[-1]
                    if last_part in SUBSTRING_FIELDS:
                        return (x and x in y) or (y and y in x) or (x == y)
                    return x == y

                if value is None:
                    return False

                if isinstance(value, str):
                    return value.strip() and len([child for child in children if same_string(child, value)]) == 0

                if isinstance(value, int):
                    return value not in children

                if isinstance(value, dict):
                    # For a dict, check if there is an element of whom all keys are identical to value's keys
                    for inner_item in children:
                        if inner_item == value:
                            return False
                    return True
                return True

            if isinstance(child_value, list):
                # Check which elements of found value can be added to children
                add = list(filter(new_instance, child_value))
                if add:
                    children = children + add

            elif new_instance(child_value):
                # Check if value found can be added to children
                children.append(child_value)

    return children


def parse_entity_fields(entity_data, fields, include_details=False, field_filters: dict = None):
    """
    For each field in given list, if it begins with adapters_data, just fetch it from corresponding adapter.
    also check for metadata
    :param entity_data:     A nested dict representing parsed values of an entity
    :param fields:          List of paths to values in the entity_data dict
    :param include_details: For each requested field, add also <field>_details,
                            containing a list of values for the field per adapter that composes the entity
    :param field_filters: Filter fields' values to those that are have a string including their matching filter
    :return:                Mapping of a field path to it's value list as found in the entity_data
    """

    def _extract_name(field_path):
        """
        Try to match given field path with the prefix of specific_data, meaning it is a generic field
        """
        match_name = re.match(r'specific_data\.data\.([\w._]*)', field_path)
        if match_name and len(match_name.groups()) == 1:
            return match_name[1]
        return None

    field_to_value = {}

    if include_details:
        adapter_datas = [item for value in sorted(set(entity_data['adapters']))
                         for item in entity_data['adapters_data'][value]]
    for field_path in fields:
        if field_path in PREFERRED_FIELDS:
            continue
        val = find_entity_field(entity_data, field_path)
        if val is not None and (not isinstance(val, (str, list)) or len(val)):
            if field_filters and field_filters.get(field_path):
                if isinstance(val, list):
                    val = [item for item in val if is_filter_in_value(item, field_filters[field_path])]
                elif is_filter_in_value(val, field_filters[field_path]):
                    val = None

            field_to_value[field_path] = val
        if not include_details:
            continue
        generic_field = _extract_name(field_path)
        field_to_value[f'{field_path}_details'] = [find_entity_field(data, generic_field) if generic_field else ''
                                                   for data in adapter_datas]

    # The next block handles columns with _preferred suffix
    # The priority order is according to here https://axonius.atlassian.net/browse/AX-6238
    # pylint: disable=too-many-nested-blocks
    for preferred_field in PREFERRED_FIELDS:
        if preferred_field not in fields:
            continue
        else:
            specific_property = preferred_field[SPECIFIC_DATA_PREFIX_LENGTH:].replace(PREFERRED_SUFFIX, '')
            if specific_property.find('.') != -1:
                specific_property, sub_property = specific_property.split('.')
            else:
                sub_property = None
            val, last_seen, sub_property_val = '', datetime(1970, 1, 1, 0, 0, 0), None
        try:
            # First priority is the latest seen Agent adapter
            for adapter in entity_data['adapters_data']:
                if not adapter.endswith('_adapter'):
                    continue
                _adapter = entity_data['adapters_data'][adapter][0]
                if 'Agent' in _adapter['adapter_properties'] and 'last_seen' in _adapter \
                        and _adapter['last_seen'] > last_seen:
                    if sub_property is not None and specific_property in _adapter:
                        try:
                            sub_property_val = _adapter[specific_property][sub_property] if \
                                isinstance(_adapter[specific_property], dict) else \
                                [x[sub_property] for x in _adapter[specific_property] if sub_property in x]
                        # Field not in result
                        except Exception:
                            sub_property_val = None
                    if specific_property in _adapter and (sub_property_val != [] and sub_property_val is not None):
                        val = sub_property_val
                    elif specific_property in _adapter and not isinstance(sub_property, str):
                        val = _adapter[specific_property]
                    else:
                        val = ''
                    if val != '':
                        last_seen = _adapter['last_seen']

            # Second priority is active-directory data
            if (val != '' and last_seen is not None and
                    (datetime.now() - last_seen).days > MAX_DAYS_SINCE_LAST_SEEN) or \
                    (last_seen is None and val == ''):
                val, last_seen = find_entity_field(entity_data,
                                                   specific_property,
                                                   specific_adapter='active_directory_adapter')
                if val is not None and sub_property is not None:
                    try:
                        sub_property_val = val[sub_property] if isinstance(val, dict) else \
                            [x[sub_property] for x in val if sub_property in x]
                    # Field not in result
                    except Exception:
                        sub_property_val = None
                if val is not None and isinstance(sub_property, str) and \
                   (sub_property_val is not None and sub_property_val != []):
                    val = sub_property_val
                elif val is None or (val is not None and isinstance(sub_property, str)) and \
                                    (sub_property_val is None or sub_property_val == []):
                    val = ''
                if val == '':
                    last_seen = datetime(1970, 1, 1, 0, 0, 0)

            # Third priority is the latest seen Assets adapter
            if (val != '' and last_seen != datetime(1970, 1, 1, 0, 0, 0) and
                    (datetime.now() - last_seen).days > MAX_DAYS_SINCE_LAST_SEEN) or \
                    (last_seen == datetime(1970, 1, 1, 0, 0, 0) and val == ''):
                if last_seen is None:
                    last_seen = datetime(1970, 1, 1, 0, 0, 0)
                if 'Assets' in _adapter['adapter_properties'] and 'last_seen' in _adapter \
                        and _adapter['last_seen'] > last_seen:
                    if sub_property is not None and specific_property in _adapter:
                        try:
                            sub_property_val = _adapter[specific_property][sub_property] if \
                                isinstance(_adapter[specific_property], dict) else \
                                [x[sub_property] for x in _adapter[specific_property] if sub_property in x]
                        # Field not in result
                        except Exception:
                            sub_property_val = None
                    if specific_property in _adapter and (sub_property_val != [] and sub_property_val is not None):
                        val = sub_property_val
                    elif specific_property in _adapter and not isinstance(sub_property, str):
                        val = _adapter[specific_property]
                    else:
                        val = ''
                    if val != '':
                        last_seen = _adapter['last_seen']

            # Forth priority is the latest seen adapter
            if (val != '' and last_seen != datetime(1970, 1, 1, 0, 0, 0) and
                    (datetime.now() - last_seen).days > MAX_DAYS_SINCE_LAST_SEEN) or \
                    (last_seen == datetime(1970, 1, 1, 0, 0, 0) and val == ''):
                for adapter in entity_data['adapters_data']:
                    if not adapter.endswith('_adapter'):
                        continue
                    _adapter = entity_data['adapters_data'][adapter][0]
                    if 'last_seen' in _adapter and _adapter['last_seen'] > last_seen:
                        if sub_property is not None and specific_property in _adapter:
                            try:
                                sub_property_val = _adapter[specific_property][sub_property] if \
                                    isinstance(_adapter[specific_property], dict) else \
                                    [x[sub_property] for x in _adapter[specific_property] if sub_property in x]
                            # Field not in result
                            except Exception:
                                sub_property_val = None
                        if specific_property in _adapter and (sub_property_val != [] and sub_property_val is not None):
                            val = sub_property_val
                        elif specific_property in _adapter and not isinstance(sub_property, str):
                            val = _adapter[specific_property]
                        else:
                            val = ''
                        if val != '':
                            last_seen = _adapter['last_seen']
            if isinstance(val, list) and isinstance(val[0], list):
                field_to_value[preferred_field] = val[0]
            elif isinstance(val, list):
                field_to_value[preferred_field] = val
            else:
                field_to_value[preferred_field] = [val]
        except Exception as e:
            logger.error(f'Problem in merging preferred fields: {e}')
            continue

    # in case the entity has meta data added like client_used
    if not include_details:
        return field_to_value

    all_metadata = _get_all_metadata_from_entity_data(entity_data)
    for field_name in all_metadata:
        field_to_value[f'meta_data.{field_name}'] = all_metadata[field_name]
    return field_to_value


def _get_all_metadata_from_entity_data(entity_data):
    all_metas = defaultdict(list)
    specific_datas = entity_data.get('specific_data', [])
    for adapter_name, field_list in entity_data.get('adapters_meta', {}).items():
        for field in field_list:
            # filed -> field value from the list eg ('client_used' : 'users_2')
            for field_name, field_value in field.items():
                # get the position to insert from the specific data
                # needed for exact pairing of the data in FE
                position = _get_adapter_position_in_specific_data(adapter_name,
                                                                  field_name,
                                                                  field_value,
                                                                  specific_datas,
                                                                  len(all_metas[field_name]))
                all_metas[field_name].insert(position, field_value)
    return all_metas


def _get_adapter_position_in_specific_data(adapter_name,  field_name, field_value, specific_datas, default_position=0):
    """
    search in specific data the position of the adapter client,
    this position is very important for the data to be valid,
    in the GUI we need to pair adapter and his data the returned position is the key for pairing the data
    :param adapter_name: the name of the adapter
    :param field_name: the metadata field name
    :param field_value: the value of that field
    :param specific_datas: the specific data dict, holds the true order of the adapters
    :param default_position: the default position to return if no position found
    :return: the position of the requested adapter data or the default position
    """
    for index, specific_data in enumerate(specific_datas):
        if specific_data.get(field_name, '') == field_value \
                and specific_data.get('plugin_name', '') == adapter_name:
            return index
    return default_position


def _is_subjson_check_list_value(subset_list, superset_list):
    subset_dicts = [item for item in subset_list if isinstance(item, dict)]
    subset_regs = [item for item in subset_list if not isinstance(item, (dict, list))]
    subset_lists = [item for item in subset_list if isinstance(item, list)]

    superset_dicts = [item for item in superset_list if isinstance(item, dict)]
    superset_regs = [item for item in superset_list if not isinstance(item, (dict, list))]
    superset_lists = [item for item in superset_list if isinstance(item, list)]

    if subset_regs != superset_regs:
        if not all(subset_reg in superset_regs for subset_reg in subset_regs):
            return False
    else:
        return True

    if not _is_subjson_check_list_value(subset_lists, superset_lists):
        return False

    if len(subset_dicts) > len(superset_dicts):
        return False

    if not all(itertools.starmap(is_subjson, zip(subset_dicts, superset_dicts))):
        return False

    return True


def _is_subjson_check_value(subset_value, superset_value):
    if type(superset_value) is not type(subset_value):
        return False

    if superset_value == subset_value:
        return True

    if isinstance(subset_value, dict):
        return is_subjson(subset_value, superset_value)

    if isinstance(subset_value, list):
        return _is_subjson_check_list_value(subset_value, superset_value)

    return False


def is_subjson(subset, superset):
    if subset.items() <= superset.items():
        return True

    if subset.items() > superset.items():
        return False

    for key, value in subset.items():
        if key not in superset:
            return False

        if not _is_subjson_check_value(value, superset[key]):
            return False
    return True


def merge_entities_fields(entities_data, fields):
    """
        find all entities that are subset of other entities, and merge them.
    """
    results = []
    parsed_entities_data = [parse_entity_fields(entity_data, fields) for entity_data in entities_data]
    # Sort list values in order to check equality of content, regardless different order
    for entity_data in parsed_entities_data:
        for value in entity_data.values():
            if not value or not isinstance(value, list) or isinstance(value[0], dict):
                continue
            value.sort()

    for subset_candidate in parsed_entities_data:
        for superset_candidate in parsed_entities_data:
            if subset_candidate == superset_candidate:
                continue

            if is_subjson(subset_candidate, superset_candidate):
                # Found subset
                break
        else:
            # Not subset of anything append to results
            if subset_candidate not in results:
                results.append(subset_candidate)
    return results


def get_sort(view):
    sort_def = view.get('sort')
    sort_obj = {}
    if sort_def and sort_def.get('field'):
        field_name_splitted: List[str] = sort_def['field'].split('.')
        if field_name_splitted[0] == SPECIFIC_DATA:
            field_name_splitted[0] = 'adapters'
        elif field_name_splitted[0] == ADAPTERS_DATA:
            field_name_splitted[0] = 'adapters'
            del field_name_splitted[1]
        field_name = '.'.join(field_name_splitted)

        sort_obj[field_name] = pymongo.DESCENDING if sort_def['desc'] else pymongo.ASCENDING
    return sort_obj


def _filter_out_nonexisting_fields(field_schema: dict, existing_fields: List[str]):
    """
    Returns a schema that consists only of fields that exist in 'existing_fields'
    :param field_schema: See 'devices_fields' collection in any adapter, where name=parsed
    :param existing_fields: See 'devices_fields' collection in any adapter, where name=exist
    """
    if not existing_fields:
        return

    def valid_items():
        for item in field_schema['items']:
            name = item['name']
            if name in existing_fields or any(x.startswith(name + '.') for x in existing_fields):
                yield item

    field_schema['items'] = list(valid_items())


@singlethreaded()
@cachetools.cached(cachetools.LRUCache(maxsize=len(EntityType)), lock=Lock())
def get_generic_fields(entity_type: EntityType):
    """
    Helper for entity_fields
    """
    if entity_type == EntityType.Devices:
        return DeviceAdapter.get_fields_info()
    if entity_type == EntityType.Users:
        return UserAdapter.get_fields_info()
    raise AssertionError


# pylint: disable=too-many-locals
@rev_cached_entity_type(ttl=60)
def entity_fields(entity_type: EntityType):
    """
    Get generic fields schema as well as adapter-specific parsed fields schema.
    Together these are all fields that any device may have data for and should be presented in UI accordingly.

    :return:
    """
    generic_fields = dict(get_generic_fields(entity_type))
    # pylint: disable=protected-access
    fields_collection = PluginBase.Instance._all_fields_db_map[entity_type]
    # pylint: enable=protected-access

    all_data_from_fields = list(fields_collection.find({}))

    global_existing_fields = [x
                              for x
                              in all_data_from_fields
                              if x['name'] == 'exist' and x.get(PLUGIN_UNIQUE_NAME) == '*']
    if global_existing_fields:
        global_existing_fields = global_existing_fields[0]

    def get_per_adapter_fields(field_name: str):
        return {
            x[PLUGIN_UNIQUE_NAME]: x
            for x
            in all_data_from_fields
            if x['name'] == field_name and PLUGIN_UNIQUE_NAME in x
        }

    per_adapter_exist_field = get_per_adapter_fields('exist')
    per_adapter_parsed_field = get_per_adapter_fields('parsed')

    if global_existing_fields:
        _filter_out_nonexisting_fields(generic_fields, global_existing_fields['fields'])

    adapters_json = {
        'name': 'adapters',
        'title': ADAPTER_CONNECTIONS_FIELD,
        'type': 'array',
        'format': 'discrete',
        'items': {
            'type': 'string',
            'format': 'logo',
            'enum': []
        },
        'sort': True,
        'unique': True
    }

    unique_adapters_json = {
        'name': 'adapter_list_length',
        'title': DISTINCT_ADAPTERS_COUNT_FIELD,
        'type': 'number',
        'sort': True
    }

    axon_id_json = {
        'name': 'internal_axon_id',
        'title': 'Asset Unique ID',
        'type': 'string'
    }

    tags_json = {
        'name': 'labels',
        'title': 'Tags',
        'type': 'array',
        'items': {
            'type': 'string',
            'format': 'tag',
            'enum': [],
            'source': {
                'key': 'all-tags',
                'options': {
                    'allow-custom-option': False
                }
            }
        }
    }

    preferred_json = [
        {
            'name': 'specific_data.data.hostname_preferred',
            'title': 'Preferred Host Name',
            'type': 'string'
        },
        {
            'name': 'specific_data.data.os.type_preferred',
            'title': 'Preferred OS Type',
            'type': 'string'
        },
        {
            'name': 'specific_data.data.os.distribution_preferred',
            'title': 'Preferred OS Distribution',
            'type': 'string'
        },
        {
            'name': 'specific_data.data.network_interfaces.mac_preferred',
            'title': 'Preferred MAC Address',
            'type': 'string'
        },
        {
            'name': 'specific_data.data.network_interfaces.ips_preferred',
            'title': 'Preferred IPs',
            'type': 'string'
        }
    ]

    generic_in_fields = [adapters_json, unique_adapters_json, axon_id_json] \
        + flatten_fields(generic_fields, 'specific_data.data', ['scanner'])\
        + [tags_json] + preferred_json
    fields = {
        'schema': {
            'generic': generic_fields,
            'specific': {}
        },
        'generic': generic_in_fields,
        'specific': {},
    }

    # pylint: disable=protected-access
    plugins_available = PluginBase.Instance._get_collection('configs', 'core').find({
        '$or': [{
            'plugin_type': {
                '$in': [
                    'Adapter', 'ScannerAdapter'
                ]
            }
        }, {
            'plugin_name': {
                '$in': [
                    'gui', 'general_info'
                ]
            }
        }]
    }, {
        PLUGIN_UNIQUE_NAME: 1, PLUGIN_NAME: 1
    })
    # pylint: enable=protected-access

    exclude_specific_schema = set(item['name'] for item in generic_fields.get('items', []))
    for plugin in plugins_available:
        plugin_unique_name = plugin[PLUGIN_UNIQUE_NAME]
        plugin_name = plugin[PLUGIN_NAME]

        plugin_fields_record = per_adapter_parsed_field.get(plugin_unique_name)
        if not plugin_fields_record:
            continue

        plugin_fields_existing = per_adapter_exist_field.get(plugin_unique_name)
        if plugin_fields_existing and plugin_name != GUI_PLUGIN_NAME:
            # We don't filter out GUI fields
            # https://axonius.atlassian.net/browse/AX-3113
            _filter_out_nonexisting_fields(plugin_fields_record['schema'], set(plugin_fields_existing['fields']))

        items = [x
                 for x
                 in plugin_fields_record['schema'].get('items', [])
                 if x['name'] not in exclude_specific_schema]
        specific_items = flatten_fields(plugin_fields_record['schema'], f'adapters_data.{plugin_name}', ['scanner'])

        # Adding adapter_count field to each adapter
        specific_items.append({
            'name': f'adapters_data.{plugin_name}.adapter_count',
            'title': DISTINCT_ADAPTERS_COUNT_FIELD,
            'type': 'number',
        })

        if items or specific_items:
            fields['schema']['specific'][plugin_name] = {
                'type': plugin_fields_record['schema']['type'],
                'required': plugin_fields_record['schema'].get('required', []),
                'items': items
            }
            fields['specific'][plugin_name] = specific_items

    return fields
# pylint: enable=too-many-locals


def get_csv(mongo_filter, mongo_sort, mongo_projection, entity_type: EntityType,
            default_sort=True, history: datetime = None, field_filters: dict = None) -> io.StringIO:
    """
    See '_get_csv' docs.
    Returns a StringIO object - not iterable
    """
    s = io.StringIO()
    list(_get_csv(mongo_filter, mongo_sort, mongo_projection, entity_type, s, default_sort, history, field_filters))
    return s


def get_csv_iterable(mongo_filter, mongo_sort, mongo_projection, entity_type: EntityType,
                     default_sort=True, history: datetime = None, field_filters: dict = None) -> Iterable[str]:
    """
    See '_get_csv' docs.
    Returns an iterator of string lines
    """

    class MyStringIo(io.StringIO):
        """
        A version of io.StringIO that just returns the strings given, makes _get_csv_iterable return the string
        that it writes
        """

        def write(self, x, *args):
            return x

    s = MyStringIo()
    return _get_csv(mongo_filter, mongo_sort, mongo_projection, entity_type, s, default_sort, history, field_filters)


def get_csv_canonized_value(value: Union[str, list, int, datetime, float, bool]) -> Union[List[str], str]:
    """
    Format dates as a pretty string or convert all value to a string
    """

    def _process_item(item):
        return item.strftime('%Y-%m-%d %H:%M:%S') if isinstance(item, datetime) else str(item)

    if isinstance(value, list):
        return ', '.join([_process_item(item) for item in value])
    return _process_item(value)


def _get_csv(mongo_filter, mongo_sort, mongo_projection, entity_type: EntityType, file_obj,
             default_sort=True, history: datetime = None, field_filters: dict = None) -> Iterable[None]:
    """
    Given a entity_type, retrieve it's entities, according to given filter, sort and requested fields.
    The resulting list is processed into csv format and returned as a file content, to be downloaded by browser.
    :param file_obj: File obj for output.
    """
    logger.info(f'Generating CSV')
    logger.debug(f'CSV filter: {mongo_filter}')
    logger.debug(f'CSV stream: {file_obj}')

    from axonius.utils.db_querying_helper import get_entities
    entities = get_entities(None, None, mongo_filter, mongo_sort,
                            mongo_projection,
                            entity_type,
                            default_sort=default_sort,
                            run_over_projection=False,
                            history_date=history,
                            ignore_errors=True,
                            field_filters=field_filters)

    current_entity_fields = entity_fields(entity_type)

    yield from serial_csv.handle_entities(
        stream=file_obj,
        entity_fields=current_entity_fields,
        selected=mongo_projection,
        entities=entities,
        excluded=[ADAPTERS_LIST_LENGTH],
        cell_joiner=serial_csv.constants.CELL_JOIN_DEFAULT,
    )


# pylint: disable=too-many-return-statements
def flatten_fields(schema, name='', exclude=None, branched=False):
    exclude = exclude or []

    def _merge_title(schema, title):
        """
        If exists, add given title before that of given schema or set it if none existing
        :param schema:
        :param title:
        :return:
        """
        new_schema = {**schema}
        if title:
            new_schema['title'] = f'{title}: {new_schema["title"]}' if new_schema.get('title') else title
        return new_schema

    if schema.get('name'):
        if schema['name'] in exclude:
            return []
        name = f'{name}.{schema["name"]}' if name else schema['name']

    if schema['type'] == 'array' and schema.get('items'):
        if isinstance(schema['items'], list):
            children = []
            for item in schema['items']:
                if not item.get('title'):
                    continue
                children = children + flatten_fields(_merge_title(item, schema.get('title')), name, exclude, branched)
            return children

        if schema['items']['type'] != 'array':
            if not schema.get('title'):
                return []
            return [{**schema, 'name': name}]

        return [{
            **schema,
            'name': name,
            'items': {
                'type': 'array',
                'items': flatten_fields(schema['items'], '', exclude)
            }
        }, *flatten_fields(_merge_title(schema['items'], schema.get('title')), name, exclude, True)]

    if not schema.get('title'):
        return []
    if branched:
        schema['branched'] = True
    return [{**schema, 'name': name}]
# pylint: enable=too-many-return-statements


def get_entity_labels(db) -> List[str]:
    """
    Find all tags that currently belong to devices, to form a set of current tag values
    :param db: the entities view db
    :return: all label strings
    """
    return [x for x in db.distinct('tags.label_value') if x]


def add_labels_to_entities(namespace: EntitiesNamespace, entities: Iterable[str], labels: Iterable[str],
                           to_delete: bool, is_huge: bool = False):
    """
    Add new tags to the list of given devices or remove tags from the list of given devices
    :param namespace: the namespace to use
    :param entities: list of internal_axon_id to tag
    :param labels: list of labels to add or remove
    :param to_delete: whether to remove the labels or to add them
    :param is_huge: If True, will use heavy_lifting plugin for assistance
    """
    from axonius.utils.db_querying_helper import iterate_axonius_entities
    entities_from_db = iterate_axonius_entities(namespace.entity, entities, projection={
        f'adapters.{PLUGIN_UNIQUE_NAME}': 1,
        f'adapters.data.id': 1,
    })

    entities = [(entity['adapters'][0][PLUGIN_UNIQUE_NAME],
                 entity['adapters'][0]['data']['id']) for entity in entities_from_db]

    namespace.add_many_labels(entities, labels=labels,
                              are_enabled=not to_delete, is_huge=is_huge)


def flatten_list(input_list):
    for item in input_list:
        if not isinstance(item, list):
            yield item
        else:
            yield from flatten_list(item)


def nongui_beautify_db_entry(entry):
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
    return tmp


def find_filter_by_name(entity_type: EntityType, name) -> Dict[str, object]:
    """
    From collection of views for given entity_type, fetch that with given name.
    Return its filter, or None if no filter.
    """
    if not name:
        return None
    view_doc = PluginBase.Instance.gui_dbs.entity_query_views_db_map[entity_type].find_one({'name': name})
    if not view_doc:
        logger.info(f'No record found for view {name}')
        return None
    return view_doc['view']


def get_string_from_field_value(base_value):
    """
    translate field value to string, for now check for datetime and parse it with
    default jsonify time format ( UTC (GMT) in RFC 1123 format )
    :param base_value: field value to parse
    :return: string
    """
    if isinstance(base_value, datetime):
        return base_value.strftime(JSONIFY_DEFAULT_TIME_FORMAT)
    return str(base_value)
