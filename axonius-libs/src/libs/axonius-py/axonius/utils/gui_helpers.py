import csv
import io
import json
import logging
from datetime import datetime

import pymongo
import requests
from flask import make_response, request, session

from axonius.adapter_base import AdapterProperty
from axonius.consts.plugin_consts import (ADAPTERS_LIST_LENGTH, PLUGIN_NAME,
                                          PLUGIN_UNIQUE_NAME)
from axonius.devices.device_adapter import DeviceAdapter
from axonius.plugin_base import EntityType, add_rule, return_error
from axonius.users.user_adapter import UserAdapter
from axonius.utils.parsing import parse_filter

logger = logging.getLogger(f'axonius.{__name__}')


# the maximal amount of data a pagination query will give
PAGINATION_LIMIT_MAX = 2000


# Caution! These decorators must come BEFORE @add_rule
def session_connection(func):
    """
    Decorator stating that the view requires the user to be connected
    """

    def wrapper(self, *args, **kwargs):
        user = session.get('user')
        if user is None:
            return return_error('You are not connected', 401)
        return func(self, *args, **kwargs)

    return wrapper


def add_rule_unauthenticated(rule, auth_method=session_connection, *args, **kwargs):
    """
    Syntactic sugar for add_rule(should_authenticate=False, ...)
    :param rule: rule name
    :param auth_method: An auth method
    :param args:
    :param kwargs:
    :return:
    """
    add_rule_res = add_rule(rule, should_authenticate=False, *args, **kwargs)
    if auth_method is not None:
        return lambda func: auth_method(add_rule_res(func))
    return add_rule_res


# Caution! These decorators must come BEFORE @add_rule
def filtered():
    """
    Decorator stating that the view supports ?filter='adapters == 'active_directory_adapter''
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            filter_obj = dict()
            try:
                filter_expr = request.args.get('filter')
                if filter_expr and filter_expr != '':
                    logger.debug(f'Parsing filter: {filter_expr}')
                    filter_obj = parse_filter(filter_expr)
            except Exception as e:
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
                    sort_obj[sort_param] = pymongo.DESCENDING if desc_param == '1' else pymongo.ASCENDING
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


def get_entities(limit, skip, view_filter, sort, projection, db_connection, entity_views_db_map,
                 entity_type: EntityType,
                 include_history=False, default_sort=True, run_over_projection=True):
    """
    Get Axonius data of type <entity_type>, from the aggregator which is expected to store them.
    """
    logger.debug(f'Fetching data for entity {entity_type.name}')
    pipeline = [{'$match': view_filter}]
    if projection and run_over_projection:
        projection['internal_axon_id'] = 1
        projection['adapters'] = 1
        projection['unique_adapter_names'] = 1
        projection['labels'] = 1
        projection[ADAPTERS_LIST_LENGTH] = 1
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
    # The reason is that sorting without the flag, causes exceeding of the memory limit.
    data_list = entity_views_db_map.aggregate(pipeline, allowDiskUse=True)

    if view_filter and not skip and request and include_history:
        # getting the original filter text on purpose.
        view_filter = request.args.get('filter')
        mongo_sort = {'desc': True, 'field': ''}
        if sort:
            desc, field = next(iter(sort.items()))
            mongo_sort = {'desc': desc, 'field': field}
        db_connection.replace_one(
            {'name': {'$exists': False}, 'view.query.filter': view_filter},
            {
                'view': {
                    'page': 0,
                    'pageSize': limit,
                    'fields': list((projection or {}).keys()),
                    'coloumnSizes': [],
                    'query': {
                        'filter': view_filter,
                        'expressions': json.loads(request.args.get('expressions', '[]'))
                    },
                    'sort': mongo_sort
                },
                'query_type': 'history',
                'timestamp': datetime.now()
            },
            upsert=True)
    if not projection:
        return [beautify_db_entry(entity) for entity in data_list]
    return [parse_entity_fields(entity, projection.keys()) for entity in data_list]


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
    if not field_path:
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
                    x = x.lower()
                    y = y.lower()
                    return x in y or y in x

                if isinstance(value, str):
                    return len([child for child in children if same_string(child, value)]) == 0
                if isinstance(value, int):
                    return value not in children
                if isinstance(value, dict):
                    # For a dict, check if there is an element of whom all keys are identical to value's keys
                    return not [item for item in children if
                                len([key for key in item.keys() if same_string(item[key], value[key])]) > 0]
                return True

            if type(child_value) == list:
                # Check which elements of found value can be added to children
                children = children + list(filter(new_instance, child_value))
            elif new_instance(child_value):
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
        field_to_value[field] = find_entity_field(entity_data, field)
    return field_to_value


def get_sort(view):
    sort_def = view.get('sort')
    sort_obj = {}
    if sort_def and sort_def.get('field'):
        sort_obj[sort_def['field']] = pymongo.DESCENDING if (sort_def['desc']) else pymongo.ASCENDING
    return sort_obj


def entity_fields(entity_type: EntityType, core_address, db_connection):
    """
    Get generic fields schema as well as adapter-specific parsed fields schema.
    Together these are all fields that any device may have data for and should be presented in UI accordingly.

    :return:
    """

    def _get_generic_fields():
        if entity_type == EntityType.Devices:
            return DeviceAdapter.get_fields_info()
        elif entity_type == EntityType.Users:
            return UserAdapter.get_fields_info()
        return dict()

    all_supported_properties = [x.name for x in AdapterProperty.__members__.values()]

    generic_fields = _get_generic_fields()
    fields = {
        'schema': {'generic': generic_fields, 'specific': {}},
        'generic': [{
            'name': 'adapters', 'title': 'Adapters', 'type': 'array', 'items': {
                'type': 'string', 'format': 'logo', 'enum': []
            }}, {
                'name': 'specific_data.adapter_properties', 'title': 'Adapter Properties', 'type': 'string',
                'enum': all_supported_properties
        }] + flatten_fields(generic_fields, 'specific_data.data', ['scanner']) + [{
            'name': 'labels', 'title': 'Tags', 'type': 'array', 'items': {'type': 'string', 'format': 'tag'}
        }],
        'specific': {}
    }
    plugins_available = requests.get(core_address + '/register').json()
    exclude_specific_schema = [item['name'] for item in generic_fields.get('items', [])]
    plugins_from_db = list(db_connection['core']['configs'].find({}).
                           sort([(PLUGIN_UNIQUE_NAME, pymongo.ASCENDING)]))
    for plugin in plugins_from_db:
        if not plugin[PLUGIN_UNIQUE_NAME] in plugins_available:
            continue
        plugin_fields = db_connection[plugin[PLUGIN_UNIQUE_NAME]][f'{entity_type.value}_fields']
        if not plugin_fields:
            continue
        plugin_fields_record = plugin_fields.find_one({'name': 'parsed'}, projection={'schema': 1})
        if not plugin_fields_record:
            continue
        fields['schema']['specific'][plugin[PLUGIN_NAME]] = {
            'type': plugin_fields_record['schema']['type'],
            'required': plugin_fields_record['schema'].get('required', []),
            'items': filter(lambda x: x['name'] not in exclude_specific_schema,
                            plugin_fields_record['schema'].get('items', []))
        }
        fields['specific'][plugin[PLUGIN_NAME]] = flatten_fields(
            plugin_fields_record['schema'], f'adapters_data.{plugin[PLUGIN_NAME]}', ['scanner'])

    return fields


def get_csv(mongo_filter, mongo_sort, mongo_projection, db_connection, entity_views_db_map, core_address,
            basic_db_connection, entity_type: EntityType, default_sort=True):
    """
    Given a entity_type, retrieve it's entities, according to given filter, sort and requested fields.
    The resulting list is processed into csv format and returned as a file content, to be downloaded by browser.

    :param mongo_filter:
    :param mongo_sort:
    :param mongo_projection:
    :param entity_type:
    :return:
    """
    logger.info('Generating csv')
    string_output = io.StringIO()
    entities = get_entities(None, None, mongo_filter, mongo_sort, mongo_projection,
                            db_connection,
                            entity_views_db_map, entity_type,
                            default_sort=default_sort, run_over_projection=False)
    output = ''
    if len(entities) > 0:
        # Beautifying the resulting csv.
        mongo_projection.pop('internal_axon_id', None)
        mongo_projection.pop('unique_adapter_names', None)
        mongo_projection.pop(ADAPTERS_LIST_LENGTH, None)
        # Getting pretty titles for all generic fields as well as specific
        current_entity_fields = entity_fields(entity_type, core_address, basic_db_connection)
        for field in current_entity_fields['generic']:
            if field['name'] in mongo_projection:
                mongo_projection[field['name']] = field['title']
        for type in current_entity_fields['specific']:
            for field in current_entity_fields['specific'][type]:
                if field['name'] in mongo_projection:
                    mongo_projection[field['name']] = f"{' '.join(type.split('_')).capitalize()}: {field['title']}"
        for current_entity in entities:
            current_entity.pop('internal_axon_id', None)
            current_entity.pop('unique_adapter_names', None)
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
        return flatten_fields(_merge_title(schema['items'], schema.get('title')), name, exclude)

    if not schema.get('title'):
        return []
    if branched:
        schema['branched'] = True
    return [{**schema, 'name': name}]
