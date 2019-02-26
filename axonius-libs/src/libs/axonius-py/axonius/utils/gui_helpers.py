import csv
import io
import json
import logging
import itertools
from datetime import datetime
from enum import Enum
from typing import NamedTuple, Iterable, List

import cachetools
import dateutil
import pymongo

from axonius.consts.gui_consts import SPECIFIC_DATA, ADAPTERS_DATA
from axonius.entities import EntitiesNamespace
from flask import request
from pymongo.errors import PyMongoError
from retry.api import retry_call

from axonius.consts.plugin_consts import (ADAPTERS_LIST_LENGTH, PLUGIN_NAME,
                                          PLUGIN_UNIQUE_NAME, GUI_NAME)
from axonius.devices.device_adapter import DeviceAdapter
from axonius.plugin_base import EntityType, add_rule, return_error, PluginBase
from axonius.users.user_adapter import UserAdapter
from axonius.utils.axonius_query_language import convert_db_entity_to_view_entity, parse_filter, \
    parse_filter_non_entities

logger = logging.getLogger(f'axonius.{__name__}')

# the maximal amount of data a pagination query will give
PAGINATION_LIMIT_MAX = 2000

FIELDS_TO_PROJECT = ['internal_axon_id', 'adapters.pending_delete', f'adapters.{PLUGIN_NAME}',
                     'tags.type', 'tags.name', f'tags.{PLUGIN_NAME}',
                     'accurate_for_datetime', ADAPTERS_LIST_LENGTH,
                     'tags.data']

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


# This is sort of an extension for the enum below, this can be used instead of PermissionLevel.* for
# marking required permissions for endpoints and it means that ReadOnly is required for GET requests
# while any other type (DELETE, PUT, POST) require ReadWrite permissions
ReadOnlyJustForGet = object()


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
            try:
                filter_expr = request.args.get('filter', '')
                history_date = request.args.get('history')
                filter_obj = parse_filter_non_entities(filter_expr, history_date)
            except Exception as e:
                logger.exception('Failed in mongo filter')
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
            try:
                filter_expr = request.args.get('filter', '')
                history_date = request.args.get('history')
                filter_obj = parse_filter(filter_expr, history_date)
            except Exception as e:
                logger.exception('Failed in mongo filter')
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
                sort_param = request.args.get('sort')
                desc_param = request.args.get('desc')
                if sort_param:
                    logger.info(f'Parsing sort: {sort_param}')
                    direction = pymongo.DESCENDING if desc_param == '1' else pymongo.ASCENDING

                    if sort_param == 'labels':
                        # TODO: Update script for this, otherwise we have to wait for a retag for sorting to work
                        sort_obj['tags.label_value'] = direction
                    else:
                        splitted = sort_param.split('.')
                        if splitted[0] == SPECIFIC_DATA or splitted[0] == ADAPTERS_DATA:
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
            fields = request.args.get('fields')
            mongo_fields = None
            if fields:
                try:
                    mongo_fields = {}
                    for field in fields.split(','):
                        mongo_fields[field] = 1
                except json.JSONDecodeError:
                    pass
            return func(self, mongo_projection=mongo_fields, *args, **kwargs)

        return actual_wrapper

    return wrap


# Caution! These decorators must come BEFORE @add_rule


def paginated(limit_max=PAGINATION_LIMIT_MAX):
    """
    Decorator stating that the view supports '?limit=X&start=Y' for pagination
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            # it's fine to raise here - an exception will be nicely JSONly displayed by add_rule
            limit = request.args.get('limit', limit_max, int)
            if limit < 0:
                raise ValueError('Limit must not be negative')
            if limit > limit_max:
                limit = limit_max
            skip = int(request.args.get('skip', 0, int))
            if skip < 0:
                raise ValueError('start must not be negative')
            return func(self, limit=limit, skip=skip, *args, **kwargs)

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
            return None

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
            history = request.args.get('history', None)
            if history:
                try:
                    history = dateutil.parser.parse(history)
                except Exception:
                    return return_error('Specified date is invalid')
            logger.info(f"historical for {history}")
            return func(self, history=history, *args, **kwargs)

        return actual_wrapper

    return wrap


def beautify_db_entry(entry):
    """
    Renames the '_id' to 'date_fetched', and stores it as an id to 'uuid' in a dict from mongo
    :type entry: dict
    :param entry: dict from mongodb
    :return: dict
    """
    tmp = {**entry, **{'date_fetched': entry['_id']}}
    tmp['uuid'] = str(entry['_id'])
    del tmp['_id']
    return tmp


def beautify_user_entry(user):
    """
    Takes a user from DB form and converts it to the form the GUI accepts.
    Takes off password field and other sensitive information.
    :param entry:
    :return:
    """
    user = beautify_db_entry(user)
    user = {k: v for k, v in user.items() if k in ['uuid',
                                                   'user_name',
                                                   'first_name',
                                                   'last_name',
                                                   'pic_name',
                                                   'permissions',
                                                   'role_name',
                                                   'admin',
                                                   'source']}
    return user


def _perform_aggregation(entity_views_db,
                         limit, skip, view_filter, sort,
                         projection, entity_type,
                         default_sort, run_over_projection):
    """
    Performs the required query on the DB using the aggregation method.
    This method is more reliable as it allows for the DB to use the disk by it is much slower in most cases.
    This should be used in cases where the regular (_perform_find) method failed.
    For parameter info see get_entities
    :return:
    """
    pipeline = [{'$match': view_filter}]
    if projection and run_over_projection:
        for field in FIELDS_TO_PROJECT:
            projection[field] = 1
        pipeline.append({'$project': projection})
    if sort:
        pipeline.append({'$sort': sort})
    elif entity_type == EntityType.Devices:
        if default_sort:
            # Default sort by adapters list size and then Mongo id (giving order of insertion)
            pipeline.append({'$sort': {ADAPTERS_LIST_LENGTH: pymongo.DESCENDING, '_id': pymongo.DESCENDING}})

    if skip:
        pipeline.append({'$skip': skip})
    if limit:
        pipeline.append({'$limit': limit})

    # Fetch from Mongo is done with aggregate, for the purpose of setting 'allowDiskUse'.
    # This allows bypassing a memory overflow occurring in Mongo
    # https://stackoverflow.com/questions/27023622/overflow-sort-stage-buffered-data-usage-exceeds-internal-limit
    # This should be used as a last resort when all other methods have failed
    def aggregate_list():
        return list(entity_views_db.aggregate(pipeline, allowDiskUse=True))

    # The reason for the retry is https://jira.mongodb.org/browse/SERVER-36737
    return retry_call(aggregate_list, tries=5)


def _perform_find(entity_views_db,
                  limit, skip, view_filter, sort,
                  projection, entity_type,
                  default_sort):
    """
    Tries to perform the given query using the 'find' method on mongo
    For parameter info see get_entities
    :raises PyMongoError: if some mongo error happened
    :return:
    """
    find_sort = list(sort.items())
    if not find_sort and entity_type == EntityType.Devices:
        if default_sort:
            # Default sort by adapters list size and then Mongo id (giving order of insertion)
            find_sort.append((ADAPTERS_LIST_LENGTH, pymongo.DESCENDING))
    return list(
        entity_views_db.find(filter=view_filter,
                             sort=find_sort,
                             projection=projection,
                             limit=limit,
                             skip=skip))


def get_entities(limit: int, skip: int,
                 view_filter: dict,
                 sort: dict,
                 projection: dict,
                 entity_type: EntityType,
                 default_sort: bool = True,
                 run_over_projection=True,
                 history_date: datetime = None,
                 ignore_errors: bool = False):
    """
    Get Axonius data of type <entity_type>, from the aggregator which is expected to store them.
    :param limit: the max amount of entities to return
    :param skip: use this only with a "sort" defined. skips a defined amount first - usually for pagination
    :param view_filter: a query to be queried for, that matches mongos's filter
    :param sort: a dict {name: pymongo.DESCENDING/ASCENDING, ...} to specify sort
    :param projection: a projection in mongo's format to project which fields are to be returned
    :param entity_type: Entity type to get
    :param default_sort: adds an optional default sort using ADAPTERS_LIST_LENGTH
    :param run_over_projection: adds some common fields to the projection
    :param history_date: the date for which to fetch, or None for latest
    :param ignore_errors: Passed to convert_db_entity_to_view_entity
    :return:
    """
    db_projection = {}
    if run_over_projection:
        for field in FIELDS_TO_PROJECT_FOR_GUI:
            if projection:
                projection[field] = 1

    if projection:
        for field, v in projection.items():
            splitted = field.split('.')
            if splitted[0] == SPECIFIC_DATA:
                splitted[0] = 'adapters'
                db_projection['.'.join(splitted)] = v
                splitted[0] = 'tags'
                db_projection['.'.join(splitted)] = v
            elif splitted[0] == ADAPTERS_DATA:
                splitted[1] = 'data'

                splitted[0] = 'adapters'
                db_projection['.'.join(splitted)] = v
                splitted[0] = 'tags'
                db_projection['.'.join(splitted)] = v
            else:
                db_projection[field] = v

    if run_over_projection or projection:
        for field in FIELDS_TO_PROJECT:
            db_projection[field] = 1

    entity_views_db = PluginBase.Instance._get_appropriate_view(history_date, entity_type)
    view_filter = get_historized_filter(view_filter, history_date)
    logger.debug(f'Fetching data for entity {entity_type.name}')
    limit = limit or 0
    skip = skip or 0

    try:
        data_list = _perform_find(entity_views_db, limit, skip, view_filter, sort, db_projection, entity_type,
                                  default_sort)
    except PyMongoError:
        try:
            logger.exception("Find couldn't handle the weight! Going to slow path")
            data_list = _perform_aggregation(entity_views_db,
                                             limit, skip, view_filter, sort,
                                             db_projection, entity_type,
                                             default_sort, run_over_projection)
        except Exception:
            logger.exception("Exception when using perform aggregation")
            raise
    except Exception:
        logger.exception("Exception when using perform find")
        raise

    for entity in data_list:
        entity = convert_db_entity_to_view_entity(entity, ignore_errors=ignore_errors)
        if not projection:
            yield beautify_db_entry(entity)
        else:
            yield parse_entity_fields(entity, projection.keys())


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


def get_entities_count(entities_filter, entity_collection, history_date: datetime = None, quick: bool = False):
    """
    Count total number of devices answering given mongo_filter.
    If "quick" is True, then will only count until 1000.
    """
    processed_filter = get_historized_filter(entities_filter, history_date)

    if quick:
        return entity_collection.count_documents(processed_filter, limit=1000)

    return entity_collection.count_documents(processed_filter)


def find_entity_field(entity_data, field_path):
    """
    Recursively expand given entity, following period separated properties of given field_path,
    until reaching the requested value

    :param entity_data: A nested dict representing parsed values of an entity
    :param field_path:  A path to a field ('.' separated chain of keys)
    :return:
    """
    if entity_data is None:
        # Return no value for this path
        return ''

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

                if not value:
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

            if type(child_value) == list:
                # Check which elements of found value can be added to children
                add = list(filter(new_instance, child_value))
                if add:
                    children = children + add

            elif new_instance(child_value) and child_value:
                # Check if value found can be added to children
                children.append(child_value)

    return children


def parse_entity_fields(entity_data, fields):
    """
    For each field in given list, if it begins with adapters_data, just fetch it from corresponding adapter.

    :param entity_data: A nested dict representing parsed values of an entity
    :param fields:      List of paths to values in the entity_data dict
    :return:            Mapping of a field path to it's value list as found in the entity_data
    """
    field_to_value = {}
    for field in fields:
        val = find_entity_field(entity_data, field)
        if val is not None and ((type(val) != str and type(val) != list) or len(val)):
            field_to_value[field] = val
    return field_to_value


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
        find all entities that are subset of other entites, and merge them.
    """
    results = []
    parsed_entities_data = [parse_entity_fields(entity_data, fields) for entity_data in entities_data]
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
        sort_obj[sort_def['field']] = pymongo.DESCENDING if (sort_def['desc']) else pymongo.ASCENDING
    return sort_obj


def _filter_out_nonexisting_fields(field_schema: dict, existing_fields: List[str]):
    """
    Returns a schema that consists only of fields that exist in "existing_fields"
    :param field_schema: See "devices_fields" collection in any adapter, where name=parsed
    :param existing_fields: See "devices_fields" collection in any adapter, where name=exist
    """

    def valid_items():
        for item in field_schema['items']:
            name = item['name']
            if name in existing_fields or any(x.startswith(name + '.') for x in existing_fields):
                yield item

    field_schema['items'] = list(valid_items())


@cachetools.cached(cachetools.LRUCache(maxsize=len(EntityType)))
def _get_generic_fields(entity_type: EntityType):
    """
    Helper for entity_fields
    """
    if entity_type == EntityType.Devices:
        return DeviceAdapter.get_fields_info()
    elif entity_type == EntityType.Users:
        return UserAdapter.get_fields_info()
    raise AssertionError


def entity_fields(entity_type: EntityType):
    """
    Get generic fields schema as well as adapter-specific parsed fields schema.
    Together these are all fields that any device may have data for and should be presented in UI accordingly.

    :return:
    """
    generic_fields = dict(_get_generic_fields(entity_type))
    fields_collection = PluginBase.Instance._all_fields_db_map[entity_type]

    all_data_from_fields = list(fields_collection.find({}))

    global_existing_fields = [x
                              for x
                              in all_data_from_fields
                              if x['name'] == 'exist' and PLUGIN_UNIQUE_NAME not in x]
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
        'title': 'Adapters',
        'type': 'array',
        'items': {
            'type': 'string',
            'format': 'logo',
            'enum': []
        },
        'sort': True,
        'unique': True
    }

    tags_json = {
        'name': 'labels',
        'title': 'Tags',
        'type': 'array',
        'items': {
            'type': 'string',
            'format': 'tag'
        }
    }

    fields = {
        'schema': {'generic': generic_fields, 'specific': {}},
        'generic': [adapters_json] + flatten_fields(generic_fields, 'specific_data.data', ['scanner']) + [tags_json],
        'specific': {},
    }

    plugins_available = PluginBase.Instance._get_collection('configs', 'core').find({
        '$or': [{
            'plugin_type': {
                '$in': [
                    'Adapter', 'ScannerAdapter'
                ]
            }
        }, {
            'plugin_name': 'gui'
        }]
    }, {
        PLUGIN_UNIQUE_NAME: 1, PLUGIN_NAME: 1
    })

    exclude_specific_schema = set(item['name'] for item in generic_fields.get('items', []))
    for plugin in plugins_available:
        plugin_unique_name = plugin[PLUGIN_UNIQUE_NAME]
        plugin_name = plugin[PLUGIN_NAME]

        plugin_fields_record = per_adapter_parsed_field.get(plugin_unique_name)
        if not plugin_fields_record:
            continue

        plugin_fields_existing = per_adapter_exist_field.get(plugin_unique_name)
        if plugin_fields_existing and plugin_name != GUI_NAME:
            # We don't filter out GUI fields
            # https://axonius.atlassian.net/browse/AX-3113
            _filter_out_nonexisting_fields(plugin_fields_record['schema'], set(plugin_fields_existing['fields']))

        fields['schema']['specific'][plugin_name] = {
            'type': plugin_fields_record['schema']['type'],
            'required': plugin_fields_record['schema'].get('required', []),
            'items': [x
                      for x
                      in plugin_fields_record['schema'].get('items', [])
                      if x['name'] not in exclude_specific_schema]
        }
        fields['specific'][plugin_name] = flatten_fields(
            plugin_fields_record['schema'], f'adapters_data.{plugin_name}', ['scanner'])

    return fields


def get_csv(mongo_filter, mongo_sort, mongo_projection, entity_type: EntityType, default_sort=True,
            history: datetime = None):
    """
    Given a entity_type, retrieve it's entities, according to given filter, sort and requested fields.
    The resulting list is processed into csv format and returned as a file content, to be downloaded by browser.
    """
    logger.info('Generating csv')
    string_output = io.StringIO()
    entities = list(get_entities(None, None, mongo_filter, mongo_sort,
                                 mongo_projection,
                                 entity_type,
                                 default_sort=default_sort,
                                 run_over_projection=False,
                                 history_date=history,
                                 ignore_errors=True))
    if len(entities) > 0:
        # Beautifying the resulting csv.
        mongo_projection.pop('internal_axon_id', None)
        mongo_projection.pop(ADAPTERS_LIST_LENGTH, None)

        # Getting pretty titles for all generic fields as well as specific
        current_entity_fields = entity_fields(entity_type)
        for field in current_entity_fields['generic']:
            if field['name'] in mongo_projection:
                mongo_projection[field['name']] = field['title']

        for type_ in current_entity_fields['specific']:
            for field in current_entity_fields['specific'][type_]:
                if field['name'] in mongo_projection:
                    mongo_projection[field['name']] = f"{' '.join(type_.split('_')).capitalize()}: {field['title']}"

        for current_entity in entities:
            current_entity.pop('internal_axon_id', None)
            current_entity.pop(ADAPTERS_LIST_LENGTH, None)

            for field in mongo_projection.keys():
                # Replace field paths with their pretty titles
                if field in current_entity:
                    current_entity[mongo_projection[field]] = current_entity[field]
                    del current_entity[field]
                    if isinstance(current_entity[mongo_projection[field]], list):
                        canonized_values = [str(val) for val in current_entity[mongo_projection[field]]]
                        current_entity[mongo_projection[field]] = ','.join(canonized_values)

        dw = csv.DictWriter(string_output, mongo_projection.values())
        dw.writeheader()
        dw.writerows(entities)

    return string_output


def flatten_fields(schema, name='', exclude=[], branched=False):
    def _merge_title(schema, title):
        """
        If exists, add given title before that of given schema or set it if none existing
        :param schema:
        :param title:
        :return:
        """
        new_schema = {**schema}
        if title:
            new_schema['title'] = f"{title}: {new_schema['title']}" if new_schema.get('title') else title
        return new_schema

    if schema.get('name'):
        if schema['name'] in exclude:
            return []
        name = f"{name}.{schema['name']}" if name else schema['name']

    if schema['type'] == 'array' and schema.get('items'):
        if type(schema['items']) == list:
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

        return [{**schema, 'name': name, 'items': flatten_fields(schema['items'], '', exclude)}] + flatten_fields(
            _merge_title(schema['items'], schema.get('title')), name, exclude, True)

    if not schema.get('title'):
        return []
    if branched:
        schema['branched'] = True
    return [{**schema, 'name': name}]


def get_entity_labels(db) -> List[str]:
    """
    Find all tags that currently belong to devices, to form a set of current tag values
    :param db: the entities view db
    :return: all label strings
    """
    # TODO: This will be slow. Cache this? It's not trivial
    return [x for x in db.distinct('tags.label_value') if x]


def add_labels_to_entities(db, namespace: EntitiesNamespace, entities: Iterable[str], labels: Iterable[str],
                           to_delete: bool):
    """
    Add new tags to the list of given devices or remove tags from the list of given devices
    :param db: the entities view db
    :param namespace: the namespace to use
    :param entities: list of internal_axon_id to tag
    :param labels: list of labels to add or remove
    :param to_delete: whether to remove the labels or to add them
    """
    entities_from_db = db.find(
        filter={
            'internal_axon_id':
                {
                    '$in': entities
                }
        },
        projection={
            f'adapters.{PLUGIN_UNIQUE_NAME}': 1,
            f'adapters.data.id': 1,
        })
    # TODO: Figure out exactly what we want to tag and how, AX-2183
    entities = [(entity['adapters'][0][PLUGIN_UNIQUE_NAME],
                 entity['adapters'][0]['data']['id']) for entity in entities_from_db]

    namespace.add_many_labels(entities, labels=labels,
                              are_enabled=not to_delete)
